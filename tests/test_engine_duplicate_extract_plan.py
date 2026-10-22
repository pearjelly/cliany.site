import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.browser.selector import ground_extract_target
from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer, _repeated_completed_extracts
from cliany_site.explorer.models import ActionStep

URL = "https://duplicate.example.test/search"
FIELDS = {"name": ""}


def extraction(selector="#results li", fields=None):
    return {"type": "extract", "selector": selector, "extract_mode": "list",
            "fields": fields if fields is not None else FIELDS, "description": "Read package rows"}


def completion(actions, count):
    return {"actions": actions, "done": True, "commands": [{
        "name": "search-packages", "description": "Search packages", "action_steps": list(range(count)),
        "args": [{"name": "query", "required": True, "default": "Alpha", "action_index": 0}],
        "expects_nonempty": False,
    }]}


FIRST = {"actions": [
    {"type": "type", "ref": "1", "value": "Alpha", "description": "Type query"},
    {"type": "click", "ref": "2", "description": "Submit query"}, extraction(),
], "commands": [], "done": False}


def prepare(mocker, monkeypatch, replies, *, steps=5):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    cfg = replace(get_config(), explore_max_steps=steps, llm_retry_max_attempts=1, vision_enabled=False)
    mocker.patch("cliany_site.explorer.engine.get_config", return_value=cfg)
    tree = {"url": URL, "title": "Packages", "element_tree": "Search controls and package lists", "screenshot": b"",
            "selector_map": {
                "1": {"role": "textbox", "name": "Search", "attributes": {}},
                "2": {"role": "button", "name": "Search", "attributes": {}},
                "3": {"role": "list", "name": "Package results", "attributes": {"id": "results"}},
                "4": {"role": "list", "name": "Other results", "attributes": {"id": "other"}},
                "7": {"role": "textbox", "name": "Quick search", "attributes": {}},
                "8": {"role": "textbox", "name": "Quick search", "attributes": {}},
            }, "extract_candidates": [
                {"role": "list", "name": "private-row-value", "semantic_name": name,
                 "selectors": [f"#{identity}"], "root_selector": f"#{identity}",
                 "anchor_attributes": {"id": identity}}
                for identity, name in (("results", "Package results"), ("other", "Other results"))
            ]}
    capture = mocker.patch(
        "cliany_site.explorer.engine.capture_axtree", AsyncMock(side_effect=lambda _s: deepcopy(tree)),
    )
    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=[
        SimpleNamespace(content=json.dumps(reply)) for reply in replies
    ]))
    mocker.patch("cliany_site.explorer.engine._get_llm", return_value=model)
    cdp = SimpleNamespace(check_available=AsyncMock(return_value=True),
                          connect=AsyncMock(return_value=AsyncMock()), disconnect=AsyncMock())
    mocker.patch("cliany_site.explorer.engine.CDPConnection", return_value=cdp)

    async def execute(session, actions, *, extraction_results, before_extract, **_kwargs):
        for index, action in enumerate(actions):
            if action["type"] == "extract":
                await before_extract(session, action, index)
                extraction_results.append({"step_index": index, "data": [
                    {key: "private-row-value" for key in action["fields"]}
                ]})
        tree["url"] = URL + "?q=Alpha"

    execution = mocker.patch("cliany_site.explorer.engine.execute_action_steps", AsyncMock(side_effect=execute))
    mocker.patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value="")
    mocker.patch("cliany_site.explorer.engine.save_extract_markdown", return_value=None)
    return model, execution, cdp, capture


async def test_completed_collection_is_reused_before_duplicate_is_recorded(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, cdp, _capture = prepare(mocker, monkeypatch, [
        FIRST, completion([extraction()], 4), completion([], 3),
    ])
    result = await WorkflowExplorer().explore(URL, "Search packages", record=False)
    assert [action.action_type for action in result.actions] == ["type", "click", "extract"]
    assert result.commands[0].action_steps == [0, 1, 2]
    assert result.commands[0].args[0]["action_index"] == 0
    assert model.ainvoke.await_count == 3
    assert sum(bool(call.args[1]) for call in execute.await_args_list) == 1
    feedback = str(model.ainvoke.await_args_list[-1].args)
    assert "已有成功集合" in feedback and "累计动作索引不变" in feedback
    correction_feedback = feedback.split("已有成功集合", 1)[1]
    assert "private-row-value" not in correction_feedback
    cdp.disconnect.assert_awaited_once()


@pytest.mark.parametrize("steps,repeats", [(2, 1), (5, 2)])
async def test_persistent_duplicate_fails_with_no_second_extraction(
    mocker, monkeypatch, tmp_home, no_llm, steps, repeats
):
    model, execute, cdp, _capture = prepare(mocker, monkeypatch, [
        FIRST, *[completion([extraction()], 4) for _ in range(repeats)],
    ], steps=steps)
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore(URL, "Search packages", record=False)
    assert caught.value.reason == "duplicate_completed_extract"
    assert model.ainvoke.await_count == 1 + repeats
    assert sum(bool(call.args[1]) for call in execute.await_args_list) == 1
    cdp.disconnect.assert_awaited_once()


async def test_duplicate_uses_existing_shared_semantic_repair_budget(mocker, monkeypatch, tmp_home, no_llm):
    ambiguous = {"actions": [{"type": "type", "ref": "7", "value": "Not dispatched"}],
                 "commands": [], "done": False}
    model, execute, _cdp, _capture = prepare(mocker, monkeypatch, [
        ambiguous, FIRST, completion([extraction()], 4),
    ])
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore(URL, "Search packages", record=False)
    assert caught.value.reason == "duplicate_completed_extract"
    assert model.ainvoke.await_count == 3
    assert sum(bool(call.args[1]) for call in execute.await_args_list) == 1


@pytest.mark.parametrize("next_actions", [
    [extraction(fields={"title": ""})],
    [extraction(selector="#other li")],
    [{"type": "click", "ref": "2"}, extraction()],
])
async def test_distinct_reads_and_intervening_actions_are_preserved(
    mocker, monkeypatch, tmp_home, no_llm, next_actions
):
    count = 3 + len(next_actions)
    model, _execute, _cdp, _capture = prepare(mocker, monkeypatch, [FIRST, completion(next_actions, count)])
    result = await WorkflowExplorer().explore(URL, "Search packages", record=False)
    assert len(result.actions) == count and model.ainvoke.await_count == 2


def collection_history(mode="list"):
    role, suffix = ("table", "tr") if mode == "table" else ("list", "li")
    tree = {"url": URL + "?q=Alpha", "selector_map": {
        "3": {"role": role, "name": "Package results", "attributes": {"id": "results"}},
    }, "extract_candidates": [{
        "role": role, "name": "Package results", "semantic_name": "Package results",
        "selectors": ["#results"], "root_selector": "#results", "anchor_attributes": {"id": "results"},
    }]}
    planned = extraction(selector=f"#results {suffix}")
    planned["extract_mode"] = mode
    target = ground_extract_target(planned["selector"], tree["selector_map"], tree["extract_candidates"])
    assert target is not None
    recorded = [ActionStep("extract", URL, selector=planned["selector"], extract_mode=mode,
                           fields_map=dict(FIELDS), extract_target=target)]
    evidence = [{"action_index": 0, "data": [{"name": "private-row-value"}]}]
    return [planned], tree, recorded, evidence


@pytest.mark.parametrize("mode", ["list", "table"])
def test_completed_collection_identity_is_grounded_after_query_update(mode):
    assert _repeated_completed_extracts(*collection_history(mode)) == [
        {"action_index": 0, "completed_action_index": 0}
    ]


def test_probe_can_be_followed_by_business_read_without_discarding_history():
    planned, tree, recorded, evidence = collection_history()
    recorded[0].purpose = "probe"
    assert _repeated_completed_extracts(planned, tree, recorded, evidence) == []
    planned[0]["purpose"] = "probe"
    assert _repeated_completed_extracts(planned, tree, recorded, evidence) == [
        {"action_index": 0, "completed_action_index": 0}
    ]
    assert len(recorded) == 1 and recorded[0].purpose == "probe"


@pytest.mark.parametrize("boundary", [
    "no_history", "intervening_action", "unobserved_previous", "new_path", "new_origin", "missing_url",
    "no_evidence", "failed", "empty", "blank_field", "boolean_index", "wrong_index", "latest_failure",
    "new_fields", "new_mode", "text_mode", "mixed_plan", "empty_plan", "unobserved_current",
    "no_current_candidates", "malformed_fields", "malformed_evidence",
])
def test_nonduplicate_and_unproven_evidence_boundaries_are_not_rejected(boundary):
    planned, tree, recorded, evidence = collection_history()
    if boundary == "no_history":
        recorded.clear()
    elif boundary == "intervening_action":
        recorded.append(ActionStep("click", URL))
    elif boundary == "unobserved_previous":
        recorded[0].extract_target = None
    elif boundary == "new_path":
        tree["url"] = URL + "/next"
    elif boundary == "new_origin":
        tree["url"] = "https://other.example.test/search"
    elif boundary == "missing_url":
        tree["url"] = ""
    elif boundary == "no_evidence":
        evidence.clear()
    elif boundary == "failed":
        evidence[0]["ok"] = False
    elif boundary == "empty":
        evidence[0]["data"] = []
    elif boundary == "blank_field":
        evidence[0]["data"] = [{"name": ""}]
    elif boundary == "boolean_index":
        evidence[0]["action_index"] = False
    elif boundary == "wrong_index":
        evidence[0]["action_index"] = 1
    elif boundary == "latest_failure":
        evidence.append({"action_index": 0, "ok": False})
    elif boundary == "new_fields":
        planned[0]["fields"] = {"title": ""}
    elif boundary == "new_mode":
        planned[0]["extract_mode"] = "table"
    elif boundary == "text_mode":
        planned[0]["extract_mode"] = recorded[0].extract_mode = "text"
    elif boundary == "mixed_plan":
        planned.append({"type": "click", "ref": "2"})
    elif boundary == "empty_plan":
        planned.clear()
    elif boundary == "unobserved_current":
        planned[0]["selector"] = "#not-observed"
    elif boundary == "no_current_candidates":
        tree["extract_candidates"] = []
    elif boundary == "malformed_fields":
        planned[0]["fields"] = "not-fields"
    elif boundary == "malformed_evidence":
        evidence[:] = [None, "not-evidence"]
    assert _repeated_completed_extracts(planned, tree, recorded, evidence) == []


def test_latest_successful_evidence_is_used_without_rewriting_history():
    planned, tree, recorded, evidence = collection_history()
    failed = {"action_index": 0, "ok": False}
    evidence.insert(0, failed)
    original = deepcopy(evidence)
    assert _repeated_completed_extracts(planned, tree, recorded, evidence) == [
        {"action_index": 0, "completed_action_index": 0}
    ]
    assert evidence == original


async def test_redundant_nonterminal_collection_plan_does_not_add_output(mocker, monkeypatch, tmp_home, no_llm):
    redundant = {"actions": [extraction()], "commands": [], "done": False}
    model, execute, _cdp, _capture = prepare(mocker, monkeypatch, [FIRST, redundant, completion([], 3)])
    result = await WorkflowExplorer().explore(URL, "Search packages", record=False)
    assert len(result.actions) == 3 and model.ainvoke.await_count == 3
    assert sum(bool(call.args[1]) for call in execute.await_args_list) == 1


async def test_explicit_interactive_confirmation_keeps_repeated_read(mocker, monkeypatch, tmp_home, no_llm):
    from cliany_site.explorer.interactive import DecisionType

    model, execute, _cdp, _capture = prepare(mocker, monkeypatch, [FIRST, completion([extraction()], 4)])
    controller = SimpleNamespace(
        prompt_action_confirmation=AsyncMock(return_value=SimpleNamespace(decision_type=DecisionType.CONFIRM)),
        ask_continue_after_done=AsyncMock(return_value=False),
    )
    mocker.patch("cliany_site.explorer.interactive.InteractiveController", return_value=controller)
    result = await WorkflowExplorer(interactive=True).explore(URL, "Search packages", record=False)
    assert len(result.actions) == 4 and model.ainvoke.await_count == 2
    assert sum(bool(call.args[1]) for call in execute.await_args_list) == 2
