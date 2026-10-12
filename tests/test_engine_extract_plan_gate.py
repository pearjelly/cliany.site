import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer


def _plan(selector):
    return {"actions": [{"type": "extract", "selector": selector, "extract_mode": "list",
                         "fields": {"title": "a", "url": "a@href"}}], "done": True,
            "commands": [{"name": "search-docs", "args": [], "action_steps": [0]}]}


def _prepare(mocker, monkeypatch, selectors, *, steps=3):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    cfg = replace(get_config(), explore_max_steps=steps, llm_retry_max_attempts=1, vision_enabled=False)
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=cfg)
    tree = {"url": "https://extract.example.test/", "title": "Search Results", "element_tree": "Result lists",
            "selector_map": {"1": {"role": "list", "name": "", "attributes": {"class": "search"},
                                    "css_candidates": ["ul.search", "ul"]}},
            "extract_candidates": [
                {"role": "list", "name": "", "selectors": ["#results li"],
                 "root_selector": "#results > ul", "anchor_attributes": {"id": "results"}},
                {"role": "list", "name": "", "selectors": ["#navigation li"],
                 "root_selector": "#navigation > ul", "anchor_attributes": {"id": "navigation"}},
            ], "screenshot": b""}
    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=[
        SimpleNamespace(content=json.dumps(_plan(selector))) for selector in selectors
    ]))
    mocker.patch("cliany_site.explorer.engine._get_llm", return_value=model)
    cdp = SimpleNamespace(check_available=AsyncMock(return_value=True),
                          connect=AsyncMock(return_value=AsyncMock()), disconnect=AsyncMock())
    mocker.patch("cliany_site.explorer.engine.CDPConnection", return_value=cdp)
    mocker.patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value=tree))
    mocker.patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.save_extract_markdown", return_value=None)

    async def execute(session, actions, *, extraction_results, before_extract, **_kwargs):
        await before_extract(session, actions[0], 0)
        assert actions[0]["selector"] == "#results li"
        extraction_results.append({"step_index": 0, "data": [{"title": "Typing", "url": "typing.html"}]})

    executor = mocker.patch("cliany_site.explorer.engine.execute_action_steps", AsyncMock(side_effect=execute))
    return model, executor, cdp


@pytest.mark.parametrize("rejected", ["ul.search li", "#invented li"])
async def test_extract_only_plan_repairs_before_execution_and_history(mocker, monkeypatch, tmp_home, no_llm, rejected):
    model, executor, _cdp = _prepare(mocker, monkeypatch, [rejected, "#results li"])
    result = await WorkflowExplorer().explore("https://extract.example.test/", "Read results", record=False)
    assert model.ainvoke.await_count == 2
    executor.assert_awaited_once()
    assert [action.selector for action in result.actions] == ["#results li"]
    assert result.commands[0].action_steps == [0]
    assert result.actions[0].extract_target["attributes"] == {"id": "results"}
    assert "尚未执行" in str(model.ainvoke.await_args_list[1].args)


@pytest.mark.parametrize("steps,selectors,calls", [(3, ["ul.search li", "#invented li"], 2),
                                                   (1, ["#invented li"], 1)])
async def test_bad_extract_plan_has_one_bounded_repair(mocker, monkeypatch, tmp_home, no_llm, steps, selectors, calls):
    model, executor, cdp = _prepare(mocker, monkeypatch, selectors, steps=steps)
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore("https://extract.example.test/", "Read results", record=False)
    assert caught.value.reason == "extract_selector_ungrounded"
    assert model.ainvoke.await_count == calls
    executor.assert_not_awaited()
    cdp.disconnect.assert_awaited_once()
