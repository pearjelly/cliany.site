import types

import pytest
from click.testing import CliRunner

from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo


@pytest.mark.parametrize("sequence", ["I", "II", "AI", "IA", "IAI", "AIA"])
def test_generated_actions_keep_order_and_execute_once(sequence):
    actions = [
        ActionStep("reuse_atom", "https://example.com", target_ref=f"atom-{index}")
        if kind == "A" else
        ActionStep("type", "https://example.com", value="{{value}}", target_name=f"input-{index}")
        for index, kind in enumerate(sequence)
    ]
    result = ExploreResult(
        pages=[PageInfo("https://example.com", "Example")], actions=actions,
        commands=[CommandSuggestion("apply-actions", "Apply actions", [{"name": "value", "required": True}], list(range(len(actions))))],
    )
    code = AdapterGenerator().generate(result, "example.com")
    module = types.ModuleType("generated_action_order")
    exec(code, module.__dict__)  # noqa: S102 - verify generated Click behavior
    module.load_atom = lambda domain, atom_id: types.SimpleNamespace(actions=[{
        "type": "click", "target_name": atom_id,
    }])
    observed = []

    def execute(steps, *args, **kwargs):
        observed.extend(steps)
        return []

    module.execute_steps_via_atoms = execute
    invocation = CliRunner().invoke(module.cli, ["apply-actions", "--value", "changed", "--json"])
    assert invocation.exit_code == 0, invocation.output
    assert [step["target_name"] for step in observed] == [
        f"atom-{index}" if kind == "A" else f"input-{index}"
        for index, kind in enumerate(sequence)
    ]
    assert all(step["value"] == "changed" for step in observed if step["type"] == "type")
