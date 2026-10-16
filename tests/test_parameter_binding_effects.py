import pytest

from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.codegen.params import ParameterBindingError, build_param_overrides
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult


@pytest.mark.parametrize("arg", [
    {"name": "query"},
    {"name": "query", "default": "different"},
])
def test_advertised_argument_without_executable_binding_is_refused(arg):
    actions = [ActionStep("navigate", "https://example.test", target_url="https://example.test/?q=Alpha")]
    with pytest.raises(ParameterBindingError):
        build_param_overrides([arg], [0], actions)


def test_later_argument_cannot_overwrite_an_earlier_input_binding():
    actions = [ActionStep("type", "https://example.test", value="Alpha")]
    args = [{"name": "query", "action_index": 0}, {"name": "other", "action_index": 0}]
    with pytest.raises(ParameterBindingError):
        build_param_overrides(args, [0], actions)


@pytest.mark.parametrize("kind,field", [("click", "value"), ("type", "description"), ("navigate", "value")])
def test_placeholder_in_a_nonexecuted_field_does_not_bind_an_argument(kind, field):
    action = ActionStep(kind, "https://example.test", target_url="https://example.test/fixed", value="Alpha")
    setattr(action, field, "{{query}}")
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "query"}], [0], [action])


def test_overriding_a_value_cannot_leave_an_embedded_argument_unused():
    action = ActionStep("type", "https://example.test", value="{{first}} {{second}}")
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "first", "action_index": 0}, {"name": "second"}], [0], [action])


def test_existing_multiple_inline_and_url_placeholders_remain_supported():
    actions = [ActionStep("type", "https://example.test", value="{{first}} {{second}}"),
               ActionStep("navigate", "https://example.test", target_url="https://example.test/?q={{query}}")]
    assert build_param_overrides([{"name": name} for name in ("first", "second", "query")], [0, 1], actions) == {}


@pytest.mark.parametrize("parameters", [{"query": "fixed"}, {"term": "query"}, {"term": "{{query}}"}])
def test_existing_atom_parameter_key_and_value_bindings_remain_supported(parameters):
    action = ActionStep("reuse_atom", "https://example.test", target_ref="search", target_attributes=parameters)
    assert build_param_overrides([{"name": "query"}], [0], [action]) == {}


def test_generator_cannot_publish_a_query_option_that_only_echoes_the_input():
    result = ExploreResult(actions=[ActionStep("navigate", "https://example.test",
                           target_url="https://example.test/?q=Alpha")], commands=[
        CommandSuggestion("search", "Search", [{"name": "query", "required": True}], [0])])
    with pytest.raises(ParameterBindingError):
        AdapterGenerator().generate(result, "example.test")


def test_binding_in_another_commands_actions_does_not_count():
    actions = [ActionStep("type", "https://example.test", value="fixed"),
               ActionStep("type", "https://example.test", value="{{query}}")]
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "query"}], [0], actions)


def test_atom_key_precedence_cannot_leave_its_value_argument_unused():
    action = ActionStep("reuse_atom", "https://example.test", target_ref="search",
                        target_attributes={"first": "second"})
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "first"}, {"name": "second"}], [0], [action])


def test_reserved_parameter_alias_is_checked_using_actual_rendered_variable():
    action = ActionStep("type", "https://example.test", value="{{ctx_2}}")
    assert build_param_overrides([{"name": "ctx"}], [0], [action]) == {}


def test_alias_shadowing_is_not_mistaken_for_two_executable_arguments():
    actions = [ActionStep("type", "https://example.test", value="{{name_1}} {{name_1_2}}")]
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "name-1"}, {"name": "name_1"}], [0], actions)
