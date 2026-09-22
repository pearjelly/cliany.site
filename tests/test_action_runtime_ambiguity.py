from unittest.mock import AsyncMock

import pytest

from cliany_site.action_runtime import _resolve_action_node


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
