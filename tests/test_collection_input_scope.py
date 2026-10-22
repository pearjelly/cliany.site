import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.codegen.collection_scope import CollectionScopeError, validate_collection_scope
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.codegen.merger import AdapterMerger
from cliany_site.explorer.analyzer import AtomExtractor
from cliany_site.explorer.engine import _apply_partition_repair, _sanitize_actions_data, _validate_command_partition
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo


def _case(first_purpose="workflow"):
    actions = [ActionStep("navigate", "https://scope.example.test", target_url="https://scope.example.test/?q=Alpha"),
               ActionStep("extract", "https://scope.example.test", extract_mode="list", selector="#results li",
                          fields_map={"title": "span"}, purpose=first_purpose),
               ActionStep("type", "https://scope.example.test", value="Alpha", target_name="Search"),
               ActionStep("extract", "https://scope.example.test", extract_mode="list", selector="#results li",
                          fields_map={"title": "span"})]
    steps = [0, 2, 3] if first_purpose == "probe" else [0, 1, 2, 3]
    command = CommandSuggestion("search", "Search", [{"name": "query", "action_index": 2}], steps, False)
    return actions, command


@pytest.mark.parametrize("mode", ["text", "attribute", "list", "table"])
def test_unmarked_business_read_before_input_fails_without_data_inspection(mode):
    actions, command = _case()
    actions[1].extract_mode = mode
    with pytest.raises(CollectionScopeError, match="参数生效前"):
        validate_collection_scope(command, actions)
    with pytest.raises(CollectionScopeError):
        AdapterGenerator().generate(ExploreResult(actions=actions, commands=[command]), "scope.example.test")


@pytest.mark.parametrize("purpose", ["probe", "baseline"])
def test_predeclared_probe_and_baseline_have_different_replay_ownership(purpose):
    actions, command = _case(purpose)
    validate_collection_scope(command, actions)
    assert (1 in command.action_steps) is (purpose == "baseline")
    assert len(actions) == 4 and actions[1].purpose == purpose


def test_probe_cannot_be_exported_even_without_args_or_with_boolean_index():
    actions, command = _case("probe")
    command.args = []
    for steps in ([0, 1, 2, 3], [True]):
        command.action_steps = steps
        with pytest.raises(CollectionScopeError, match="结构探测"):
            validate_collection_scope(command, actions)


def test_auto_detected_inputs_and_reordered_replay_cannot_hide_early_reads():
    actions, command = _case()
    command.args = []
    actions[2].value = "{{query}}"
    with pytest.raises(CollectionScopeError):
        validate_collection_scope(command, actions)
    command.action_steps = [0, 3, 2, 1]
    with pytest.raises(CollectionScopeError):
        validate_collection_scope(command, actions)


def test_hidden_nonread_probe_is_rejected_even_when_not_owned_by_a_command():
    actions, command = _case("probe")
    actions[0].purpose = "probe"
    command.action_steps = [2, 3]
    with pytest.raises(CollectionScopeError):
        AdapterGenerator().generate(ExploreResult(actions=actions, commands=[command]), "scope.example.test")
    with pytest.raises(CollectionScopeError):
        AdapterMerger("scope.example.test").merge_commands([], [command], actions)


def test_multi_input_multi_collection_and_unparameterized_reads_remain_supported():
    actions = [ActionStep("type", "https://scope.example.test", target_ref="1", value="Alpha"),
               ActionStep("extract", "https://scope.example.test", extract_mode="list"),
               ActionStep("type", "https://scope.example.test", target_ref="2", value="Beta"),
               ActionStep("extract", "https://scope.example.test", extract_mode="list")]
    command = CommandSuggestion("compare", "Compare", [{"name": "first", "action_index": 0},
                                 {"name": "second", "action_index": 2}], [0, 1, 2, 3])
    validate_collection_scope(command, actions)
    command.args = []
    validate_collection_scope(command, list(reversed(actions)))


def test_partition_keeps_original_probe_indices_without_allowing_business_omission():
    _validate_command_partition([{"action_steps": [0, 2, 3]}], 4, {1})
    for steps in ([0, 1, 2, 3], [0, 2], [0, True, 2, 3]):
        with pytest.raises(RuntimeError):
            _validate_command_partition([{"action_steps": steps}], 4, {1})
    original = [{"name": "search", "action_steps": [0, 1, 2, 3], "args": [{"name": "query", "action_index": 2}]}]
    repaired = {"actions": [], "done": True, "commands": [{"name": "search", "action_steps": [0, 2, 3]}]}
    result = _apply_partition_repair(original, repaired, 4, {1})
    assert result[0]["args"] == original[0]["args"]


@pytest.mark.parametrize("purpose,kind", [("probe", "click"), ("baseline", "type"), ("unknown", "extract"),
                                          (False, "extract"), (None, "extract")])
def test_invalid_or_nonread_purpose_is_refused_before_execution(purpose, kind):
    with pytest.raises(RuntimeError) as caught:
        _sanitize_actions_data([{"type": kind, "purpose": purpose}], "https://scope.example.test")
    assert caught.value.reason == "invalid_action_purpose"


def test_complete_probe_history_survives_save_and_merge_without_rebasing(tmp_home):
    domain = "scope.example.test"
    actions, command = _case("probe")
    result = ExploreResult(pages=[PageInfo("https://scope.example.test", "Search")],
                           actions=actions, commands=[command])
    path = save_adapter(domain, AdapterGenerator().generate(result, domain), explore_result=result)
    metadata_path = Path(path).parent / "metadata.json"
    before = json.loads(metadata_path.read_text())
    history = before["exploration_history"]
    assert len(history[0]["actions"]) == 4 and history[0]["actions"][1]["purpose"] == "probe"
    assert history[0]["commands"][0]["action_steps"] == [0, 2, 3]
    assert len(before["commands"][0]["actions"]) == 3
    incoming_actions, incoming = _case("baseline")
    incoming.name = "compare"
    AdapterMerger(domain).merge(ExploreResult(actions=incoming_actions, commands=[incoming]))
    after = json.loads(metadata_path.read_text())
    assert after["exploration_history"] == history
    assert after["commands"][1]["actions"][1]["purpose"] == "baseline"
    incoming_actions, incoming = _case("probe")
    incoming.name = "new-search"
    AdapterMerger(domain).merge(ExploreResult(actions=incoming_actions, commands=[incoming]))
    after = json.loads(metadata_path.read_text())
    assert after["exploration_history"][0] == history[0] and len(after["exploration_history"]) == 2
    assert after["exploration_history"][1]["commands"][0]["action_steps"] == [0, 2, 3]
    assert incoming.args[0]["action_index"] == 2


def test_save_appends_supplied_history_without_mutating_it(tmp_home):
    actions, command = _case("probe")
    result = ExploreResult(actions=actions, commands=[command])
    old = [{"actions": [{"purpose": "probe"}], "commands": []}]
    path = save_adapter("scope.example.test", AdapterGenerator().generate(result, "scope.example.test"),
                        metadata={"exploration_history": old}, explore_result=result)
    history = json.loads((Path(path).parent / "metadata.json").read_text())["exploration_history"]
    assert history[0] == old[0] and len(history) == 2 and len(old) == 1


async def test_atom_generation_excludes_probe_inputs_and_refuses_probe_outputs(tmp_home):
    actions, command = _case("probe")
    actions[1].description = "PROBE_ONLY_SENTINEL"
    model = SimpleNamespace(ainvoke=AsyncMock(return_value='{"atoms": []}'))
    extractor = AtomExtractor(model, "scope.example.test")
    assert await extractor.extract_atoms(ExploreResult(actions=actions, commands=[command])) == []
    assert "PROBE_ONLY_SENTINEL" not in model.ainvoke.call_args.args[0]
    raw = {"atom_id": "probe-atom", "actions": [{"action_type": "extract", "purpose": "probe"}]}
    assert extractor._to_atom(raw, "Search") is None
    raw["actions"][0]["purpose"] = "baseline"
    assert extractor._to_atom(raw, "Compare") is not None
