import pytest
from click.testing import CliRunner

from cliany_site.codegen.dedup import (
    deduplicate_parameterized_actions,
    remove_consecutive_duplicate_clicks,
    remove_redundant_duplicate_actions,
)
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.codegen.params import build_param_overrides
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.loader import load_adapter


@pytest.mark.parametrize("different", [{"page_url": "https://example.com/second"}, {"target_ref": "2"},
                                      {"target_url": "https://example.com/other"}])
def test_distinct_targets_are_not_merged_by_label(different):
    base = {"page_url": "https://example.com/first", "target_ref": "1", "target_name": "Name",
            "target_role": "textbox"}
    actions = [ActionStep("type", value="recorded", **base), ActionStep("type", value="fixed", **(base | different))]
    overrides = build_param_overrides([{"name": "name", "action_index": 0}], [0, 1], actions)
    assert overrides == {0: "{{name}}"}
    assert deduplicate_parameterized_actions([0, 1], actions, overrides) == [0, 1]
    for action in actions:
        action.action_type = "click"
        action.target_role = "button"
        action.value = ""
    assert remove_consecutive_duplicate_clicks([0, 1], actions) == [0, 1]
    assert remove_redundant_duplicate_actions([0, 1], actions, {}) == [0, 1]


def test_generated_command_preserves_other_pages_fixed_input(tmp_home, monkeypatch):
    first, second = "https://example.com/first", "https://example.com/second"
    actions = [
        ActionStep("type", first, target_ref="1", target_name="Name", target_role="textbox", value="recorded"),
        ActionStep("navigate", first, target_url=second),
        ActionStep("type", second, target_ref="1", target_name="Name", target_role="textbox", value="fixed"),
    ]
    result = ExploreResult(pages=[PageInfo(first, "First"), PageInfo(second, "Second")], actions=actions,
                           commands=[CommandSuggestion("fill", "Fill both pages", [
                               {"name": "name", "action_index": 0, "required": True},
                           ], [0, 1, 2])])
    dispatched = []

    def execute(steps, *args, **kwargs):
        dispatched.extend(steps)
        return []

    monkeypatch.setattr("cliany_site.codegen.runtime_helpers.execute_steps_via_atoms", execute)
    save_adapter("example.com", AdapterGenerator().generate(result, "example.com"), explore_result=result)
    cli = load_adapter("example.com")
    assert cli is not None
    invocation = CliRunner().invoke(cli, ["fill", "--name", "changed", "--json"])
    assert invocation.exit_code == 0, invocation.output
    assert [step["type"] for step in dispatched] == ["type", "navigate", "type"]
    assert [step["value"] for step in dispatched if step["type"] == "type"] == ["changed", "fixed"]
