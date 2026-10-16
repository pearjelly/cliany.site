import pytest

from cliany_site.action_runtime import substitute_parameters
from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.codegen.params import build_param_overrides
from cliany_site.codegen.templates import render_action_data_literal
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult


@pytest.mark.parametrize("kind", ["navigate", "click", "submit", "extract", "reuse_atom"])
@pytest.mark.parametrize("explicit", [True, False])
def test_value_parameter_cannot_bind_to_a_step_that_does_not_consume_it(kind, explicit):
    actions = [ActionStep(kind, "https://example.test/search", value="Alpha",
                          target_url="https://example.test/search?q=Alpha")]
    arg = {"name": "query", "default": "Alpha"}
    if explicit:
        arg["action_index"] = 0
    with pytest.raises(ValueError, match="参数绑定"):
        build_param_overrides([arg], [0], actions)


@pytest.mark.parametrize("kind", ["type", "select"])
def test_executable_value_binding_preserves_changed_and_zero_match_inputs(kind):
    import json

    actions = [ActionStep(kind, "https://example.test/search", value="Alpha")]
    overrides = build_param_overrides([{"name": "query", "action_index": 0}], [0], actions)
    emitted = json.loads(render_action_data_literal([0], actions, overrides))
    for query in ("Gamma", "no-match"):
        assert substitute_parameters(emitted, {"query": query})[0]["value"] == query
    assert actions[0].value == "Alpha"


def test_generator_does_not_publish_a_fixed_navigation_query_as_parameterized():
    actions = [ActionStep("navigate", "https://example.test/search",
                          target_url="https://example.test/search?q=Alpha")]
    command = CommandSuggestion("search", "Search", [
        {"name": "query", "required": True, "action_index": 0, "default": "Alpha"},
    ], [0])
    with pytest.raises(ValueError, match="参数绑定"):
        AdapterGenerator().generate(ExploreResult(actions=actions, commands=[command]), "example.test")


def test_existing_explicit_url_placeholder_is_not_invented_or_rewritten():
    actions = [ActionStep("navigate", "https://example.test/search",
                          target_url="https://example.test/search?q={{query}}")]
    assert build_param_overrides([{"name": "query"}], [0], actions) == {}
