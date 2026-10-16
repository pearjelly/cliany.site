import json

import pytest

from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer, _invalid_command_parameter_bindings
from cliany_site.explorer.models import ActionStep
from tests.test_engine_semantic_plan_gate import _plan, _prepare


def _binding_plan(kind="navigate", *, index=0):
    plan = _plan("3")
    plan["actions"] = [{"type": kind, "url": "https://plan.example.test/?q=private-input-value",
                        "ref": "3", "value": "private-input-value"}]
    plan["commands"][0]["args"] = [{"name": "query", "required": True, "action_index": index,
                                     "default": "private-input-value"}]
    return plan


@pytest.mark.parametrize("kind", ["navigate", "click", "submit", "extract"])
async def test_unsupported_binding_is_replanned_before_execution(kind, mocker, monkeypatch, tmp_home, no_llm):
    model, execute, cdp = _prepare(mocker, monkeypatch, [_binding_plan(kind), _binding_plan("type")])
    result = await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert model.ainvoke.await_count == 2
    execute.assert_awaited_once()
    assert [action.action_type for action in result.actions] == ["type"]
    assert result.commands[0].args[0]["action_index"] == 0
    feedback = str(model.ainvoke.await_args_list[1].args).split("命令参数绑定门禁：", 1)[1]
    assert "尚未执行" in feedback and "private-input-value" not in feedback
    cdp.disconnect.assert_awaited_once()


@pytest.mark.parametrize("second", ["repeat", "remove", "ambiguity"])
async def test_one_shared_repair_cannot_be_reset_or_drop_the_advertised_parameter(
    second, mocker, monkeypatch, tmp_home, no_llm,
):
    correction = _binding_plan()
    if second == "remove":
        correction["commands"][0]["args"] = []
    elif second == "ambiguity":
        correction = _binding_plan("type")
        correction["actions"][0]["ref"] = "1"
    model, execute, _ = _prepare(mocker, monkeypatch, [_binding_plan(), correction], steps=5)
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert caught.value.reason == ("action_target_ambiguous" if second == "ambiguity" else "parameter_binding_invalid")
    assert model.ainvoke.await_count == 2
    execute.assert_not_awaited()


async def test_last_step_refuses_without_an_extra_model_call(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, _ = _prepare(mocker, monkeypatch, [_binding_plan()], steps=1)
    with pytest.raises(ExploreContractError, match="参数绑定") as caught:
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert caught.value.reason == "parameter_binding_invalid"
    model.ainvoke.assert_awaited_once()
    execute.assert_not_awaited()


async def test_binding_repair_does_not_get_a_second_budget_after_ambiguity(mocker, monkeypatch, tmp_home, no_llm):
    model, execute, _ = _prepare(mocker, monkeypatch, [_plan("1"), _binding_plan()], steps=5)
    with pytest.raises(ExploreContractError) as caught:
        await WorkflowExplorer().explore("https://plan.example.test/", "Enter a query", record=False)
    assert caught.value.reason == "parameter_binding_invalid"
    assert model.ainvoke.await_count == 2
    execute.assert_not_awaited()


def test_recorded_navigation_is_checked_without_copying_values_or_urls():
    recorded = [ActionStep("navigate", "https://example.test", target_url="https://example.test/?q=private")]
    plan = _binding_plan()
    assert _invalid_command_parameter_bindings({**plan, "actions": []}, [], recorded, set()) == [{
        "command_index": 0, "parameter_name": "query", "action_index": 0, "action_type": "navigate",
    }]
    assert "private" not in json.dumps(_invalid_command_parameter_bindings(plan, [], recorded, set()))


def test_nonterminal_and_existing_partition_ownership_policy_are_not_rewritten():
    assert _invalid_command_parameter_bindings({**_binding_plan(), "done": False}, [], [], set()) == []
    assert _invalid_command_parameter_bindings(_binding_plan(index=99), [], [], set()) == []
