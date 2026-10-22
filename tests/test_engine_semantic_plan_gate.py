import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer, _observed_prefix_before_unobserved_extract


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


@pytest.fixture
def unobserved_extract_tree():
    return {"url": "https://plan.example.test/", "element_tree": "Observed entry",
            "selector_map": {
                "1": {"role": "link", "name": "Full Search", "attributes": {"href": "/next"}},
                "3": {"role": "textbox", "name": "Query", "attributes": {"id": "query"}},
            }, "extract_candidates": [
                {"role": "list", "name": "Sections", "semantic_name": "Sections",
                 "selectors": ["#sections"], "root_selector": "#sections", "anchor_attributes": {"id": "sections"}},
                {"role": "list", "selectors": ["ul.search"], "root_selector": "ul.search"},
                {"role": "list", "selectors": ["#other"], "root_selector": "#other"},
            ]}


@pytest.mark.parametrize(("prefix", "selector", "expected"), [
    ([{"type": "click", "ref": "@1"}], "#future li", 1),
    ([{"type": "navigate", "url": "https://plan.example.test/next"}], "#future li", 1),
    ([{"type": "navigate", "url": "https://plan.example.test/"}], "#future li", 1),
    ([{"type": "navigate", "url": "https://plan.example.test/next?q=guessed"}], "#future li", 0),
    ([{"type": "click", "ref": "missing"}], "#future li", 0),
    ([{"type": "submit"}], "#future li", 0),
    ([{"type": "type", "ref": "3", "value": "Ada"}, {"type": "submit"}], "#future li", 2),
    ([{"type": "extract", "selector": "#sections li"}], "#future li", 0),
    ([{"type": "reuse_atom", "reuse_atom": "search"}], "#future li", 0),
    ([{"type": "click", "ref": "1"}], "ul.search li", 0),
    ([{"type": "click", "ref": "1"}], "#sections li", 0),
    ([], "#future li", 0),
])
def test_repair_prefix_requires_observed_actions_and_an_unobserved_read(
    unobserved_extract_tree, prefix, selector, expected,
):
    actions = [*prefix, {"type": "extract", "selector": selector, "extract_mode": "list"}]
    original = deepcopy((actions, unobserved_extract_tree))
    failures = [{"action_index": len(prefix)}]
    assert _observed_prefix_before_unobserved_extract(actions, unobserved_extract_tree, failures) == expected
    assert (actions, unobserved_extract_tree) == original


@pytest.mark.parametrize(("done", "next_url", "executions"), [(False, "", 1), (True, "", 0), (False, "/next", 0)])
async def test_deferred_read_still_consumes_the_one_shared_repair(
    mocker, monkeypatch, tmp_home, no_llm, unobserved_extract_tree, done, next_url, executions,
):
    plan = {"actions": [{"type": "click", "ref": "1"},
                        {"type": "extract", "selector": "#future li", "extract_mode": "list"}],
            "done": done, "next_url": next_url}
    model, execute, cdp = _prepare(mocker, monkeypatch, [plan, plan], steps=5)
    mocker.patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value=unobserved_extract_tree))
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore(unobserved_extract_tree["url"], "Search", record=False)
    assert caught.value.reason == "extract_selector_ungrounded"
    assert model.ainvoke.await_count == 2
    assert execute.await_count == executions
    if executions:
        assert execute.await_args.args[1] == [{"type": "click", "ref": "1"}]
    cdp.disconnect.assert_awaited_once()
