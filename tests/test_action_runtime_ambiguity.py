from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.action_runtime import (
    _attempt_adaptive_repair,
    _attempt_vision_locate,
    _resolve_action_node,
    _score_candidate,
)


@pytest.mark.parametrize("candidate", [
    {"name": "Cancel", "role": "button", "attributes": {"id": "apply", "class": "primary"}},
    {"name": "", "role": "button"},
    {"name": "Apply", "role": "link"},
    {"name": "Apply", "role": ""},
])
def test_conflicting_semantics_cannot_be_offset_by_other_scores(candidate):
    assert _score_candidate({
        "target_name": "Apply", "target_role": "button", "target_attributes": {"id": "apply", "class": "primary"},
    }, candidate, "") == 0


@pytest.mark.asyncio
async def test_model_repair_cannot_override_recorded_name(monkeypatch):
    session = AsyncMock()
    tree = {"selector_map": {"1": {"name": "Cancel", "role": "button"}}}
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content='{"selectors": ["1"]}')))
    monkeypatch.setattr("cliany_site.explorer.engine._get_replay_llm", lambda **kwargs: model)
    monkeypatch.setattr("cliany_site.action_runtime.capture_axtree", AsyncMock(return_value=tree))
    monkeypatch.setattr("cliany_site.action_runtime.serialize_axtree", lambda tree: "Cancel button")
    monkeypatch.setattr("cliany_site.action_runtime._get_adaptive_repair_max_attempts", lambda: 1)

    result = await _attempt_adaptive_repair(session, {"target_name": "Apply", "target_role": "button"})

    assert result is None
    model.ainvoke.assert_awaited_once()
    session.get_element_by_index.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["Apply", "Cancel"])
async def test_vision_suggestion_must_match_recorded_semantics(monkeypatch, name):
    session = AsyncMock()
    cfg = SimpleNamespace(vision_enabled=True, screenshot_format="png", screenshot_quality=75,
                          vision_som_max_labels=50, vision_min_confidence=0.8)
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=SimpleNamespace(content="unused")))
    tree = {"selector_map": {"1": {"name": name, "role": "button"}}}
    monkeypatch.setattr("cliany_site.config.get_config", lambda: cfg)
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **kwargs: model)
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", AsyncMock(return_value=tree))
    monkeypatch.setattr("cliany_site.browser.axtree.serialize_axtree", lambda tree: name)
    monkeypatch.setattr("cliany_site.browser.screenshot.capture_screenshot", AsyncMock(return_value=b"image"))
    monkeypatch.setattr("cliany_site.browser.screenshot.enrich_selector_map_with_bounds", AsyncMock(return_value={}))
    monkeypatch.setattr("cliany_site.browser.screenshot.annotate_screenshot_with_som", lambda *a, **kw: (b"image", {}))
    monkeypatch.setattr("cliany_site.explorer.vision.build_vision_locate_message", lambda *a, **kw: "prompt")
    monkeypatch.setattr("cliany_site.explorer.vision.parse_vision_locate_response",
                        lambda text: {"ref": "1", "confidence": 1.0})

    result = await _attempt_vision_locate(session, {"target_name": "Apply", "target_role": "button"})

    if name == "Apply":
        assert result is session.get_element_by_index.return_value
        session.get_element_by_index.assert_awaited_once_with(1)
    else:
        assert result is None
        session.get_element_by_index.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("ref", ["1", "999"])
async def test_tied_semantic_candidates_are_not_resolved_or_repaired(monkeypatch, ref):
    session = AsyncMock()
    tree = {"selector_map": {
        "1": {"name": "Apply", "role": "button"},
        "2": {"name": "Apply", "role": "button"},
    }}
    monkeypatch.setattr("cliany_site.action_runtime.capture_axtree", AsyncMock(return_value=tree))
    repair = AsyncMock()
    vision = AsyncMock()
    monkeypatch.setattr("cliany_site.action_runtime._attempt_adaptive_repair", repair)
    monkeypatch.setattr("cliany_site.action_runtime._attempt_vision_locate", vision)

    result = await _resolve_action_node(session, {"ref": ref, "target_name": "Apply", "target_role": "button"})

    assert result is None
    session.get_element_by_index.assert_not_awaited()
    repair.assert_not_awaited()
    vision.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_ref_cannot_override_stronger_semantic_candidate(monkeypatch):
    session = AsyncMock()
    tree = {"selector_map": {
        "1": {"name": "Cancel", "role": "button"},
        "2": {"name": "Apply", "role": "button"},
    }}
    monkeypatch.setattr("cliany_site.action_runtime.capture_axtree", AsyncMock(return_value=tree))

    await _resolve_action_node(session, {"ref": "1", "target_name": "Apply", "target_role": "button"})

    session.get_element_by_index.assert_awaited_once_with(2)


@pytest.mark.asyncio
async def test_recorded_frame_can_disambiguate_identical_labels(monkeypatch):
    session = AsyncMock()
    tree = {"selector_map": {
        "1": {"name": "Apply", "role": "button", "frame_id": "other"},
        "2": {"name": "Apply", "role": "button", "frame_id": "target"},
    }}
    monkeypatch.setattr("cliany_site.action_runtime.capture_axtree", AsyncMock(return_value=tree))

    await _resolve_action_node(session, {
        "ref": "1", "target_name": "Apply", "target_role": "button", "target_frame_id": "target",
    })

    session.get_element_by_index.assert_awaited_once_with(2)
