import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer


def _plan(ref):
    return {"actions": [{"type": "type", "ref": ref, "value": "private-input-value"}],
            "commands": [{"name": "enter-query", "action_steps": [0], "args": []}], "done": True}


def _prepare(mocker, monkeypatch, plans, *, steps=2, distinct=False):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    cfg = replace(get_config(), explore_max_steps=steps, llm_retry_max_attempts=1, vision_enabled=False)
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=cfg)
    tree = {"url": "https://plan.example.test/", "title": "Search", "element_tree": "Search controls",
            "selector_map": {
                "1": {"role": "searchbox", "name": "Quick search", "attributes": {"id": "first"} if distinct else {}},
                "2": {"role": "searchbox", "name": "Quick search", "attributes": {"id": "second"} if distinct else {}},
                "3": {"role": "textbox", "name": "Search", "attributes": {}},
            }, "screenshot": b""}
    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=[
        SimpleNamespace(content=json.dumps(plan)) for plan in plans
    ]))
    mocker.patch("cliany_site.explorer.engine._get_llm", return_value=model)
    cdp = SimpleNamespace(check_available=AsyncMock(return_value=True),
                          connect=AsyncMock(return_value=AsyncMock()), disconnect=AsyncMock())
    mocker.patch("cliany_site.explorer.engine.CDPConnection", return_value=cdp)
    mocker.patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value=tree))
    execute = mocker.patch("cliany_site.explorer.engine.execute_action_steps", AsyncMock())
    mocker.patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value="")
    return model, execute, cdp


async def test_ambiguous_plan_is_replanned_before_record_or_execution(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, cdp = _prepare(mocker, monkeypatch, [_plan("@1"), _plan("3")])
    result = await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert model.ainvoke.await_count == 2
    execute.assert_awaited_once()
    assert execute.await_args.args[1][0]["ref"] == "3"
    assert [a.target_ref for a in result.actions] == ["3"]
    assert result.commands[0].action_steps == [0]
    feedback = str(model.ainvoke.await_args_list[1].args)
    assert "尚未执行" in feedback
    assert "private-input-value" not in feedback
    cdp.disconnect.assert_awaited_once()


async def test_repeated_ambiguity_fails_after_one_repair(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, cdp = _prepare(mocker, monkeypatch, [_plan("1"), _plan("2")], steps=5)
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert caught.value.reason == "action_target_ambiguous"
    assert "private-input-value" not in str(caught.value)
    assert model.ainvoke.await_count == 2
    execute.assert_not_awaited()
    cdp.disconnect.assert_awaited_once()


async def test_last_step_does_not_issue_an_extra_repair(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, cdp = _prepare(mocker, monkeypatch, [_plan("1")], steps=1)
    with pytest.raises(ExploreContractError):
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    model.ainvoke.assert_awaited_once()
    execute.assert_not_awaited()
    cdp.disconnect.assert_awaited_once()


async def test_observed_distinct_attributes_preserve_unique_plan(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, _cdp = _prepare(mocker, monkeypatch, [_plan("1")], distinct=True)
    result = await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    model.ainvoke.assert_awaited_once()
    execute.assert_awaited_once()
    assert result.actions[0].target_ref == "1"
    assert result.actions[0].target_attributes == {"id": "first"}


async def test_empty_observation_is_recaptured_before_model_planning(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, _cdp = _prepare(mocker, monkeypatch, [_plan("3")])
    capture = mocker.patch("cliany_site.explorer.engine.capture_axtree")
    ready = {"url": "https://plan.example.test/", "element_tree": "Search controls",
             "selector_map": {"3": {"role": "textbox", "name": "Search", "attributes": {}}}}
    capture.side_effect = [{"url": ready["url"], "element_tree": "", "selector_map": {}}, ready]
    result = await WorkflowExplorer().explore(ready["url"], "Enter a query", record=False)
    assert capture.await_count == 2
    model.ainvoke.assert_awaited_once()
    execute.assert_awaited_once()
    assert result.actions[0].target_name == "Search"


async def test_persistent_empty_observation_never_calls_model(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, cdp = _prepare(mocker, monkeypatch, [_plan("3")])
    capture = mocker.patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value={
        "url": "https://plan.example.test/", "element_tree": "", "selector_map": {},
    }))
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert caught.value.reason == "page_observation_empty"
    assert capture.await_count == 2
    model.ainvoke.assert_not_awaited()
    execute.assert_not_awaited()
    cdp.disconnect.assert_awaited_once()


async def test_last_empty_observation_does_not_add_a_step(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, _cdp = _prepare(mocker, monkeypatch, [_plan("3")], steps=1)
    capture = mocker.patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value={}))
    with pytest.raises(ExploreContractError, match="AX"):
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    capture.assert_awaited_once()
    model.ainvoke.assert_not_awaited()
    execute.assert_not_awaited()


async def test_text_only_observation_is_not_treated_as_blank(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, _cdp = _prepare(mocker, monkeypatch, [_plan("3")], steps=1)
    capture = mocker.patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value={
        "url": "https://plan.example.test/", "element_tree": "Observed read-only page text", "selector_map": {},
    }))
    await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    capture.assert_awaited_once()
    model.ainvoke.assert_awaited_once()
    execute.assert_awaited_once()
