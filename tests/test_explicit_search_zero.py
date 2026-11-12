import json

import pytest

from cliany_site.action_runtime import substitute_parameters
from cliany_site.browser.search_result import ground_empty_result_recipe, observed_search_outcome
from cliany_site.browser.selector import MAIN_RESULT_LIST_ROOT, MAIN_RESULT_LIST_SCOPE
from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.commands.browser.extract import _parse_target_json
from cliany_site.envelope import ErrorCode
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import _bind_explicit_empty_result
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo

START = "https://registry.example/"
RESULT = "https://registry.example/search?q=green+tea"
MESSAGE = "0 crates found."


def _target():
    return {"role": "list", "name": "", "attributes": {}, "suffix": "", "scope": MAIN_RESULT_LIST_SCOPE}


def _explored():
    return ExploreResult(
        pages=[PageInfo(START, "Registry")],
        actions=[
            ActionStep("type", START, value="green tea", target_role="searchbox", target_name="Search"),
            ActionStep("click", START, target_role="button", target_name="Search"),
            ActionStep(
                "extract", RESULT, selector=MAIN_RESULT_LIST_ROOT, extract_mode="list", extract_target=_target(),
            ),
        ],
        commands=[CommandSuggestion("search", "Search", [{"name": "query", "action_index": 0}], [0, 1, 2], False)],
    )


def _observation():
    return {
        "url": RESULT,
        "main_result_context": {"heading": "Search for 'green tea'", "collections": 1, "busy": False},
    }


def test_recorded_positive_query_is_bound_without_storing_the_sample_as_the_replay_value():
    explored = _explored()
    _bind_explicit_empty_result(explored, {2: _observation()}, MESSAGE)
    target = explored.actions[2].extract_target
    assert target["empty_result"] == {
        "page": "https://registry.example/search", "parameter": "q", "heading_prefix": "Search for '",
        "heading_suffix": "'", "message": MESSAGE, "query": "{{query}}",
    }
    code = AdapterGenerator().generate(explored, "registry.example")
    assert "execute_query_scoped_extract_steps_via_atoms as execute_steps_via_atoms" in code
    assert _parse_target_json(json.dumps(target))["error"]["code"] == ErrorCode.E_INVALID_PARAM
    changed = substitute_parameters([{"extract_target": target}], {"query": "c++ & tools"})[0]["extract_target"]
    assert _parse_target_json(json.dumps(changed)) == changed
    assert target["empty_result"]["query"] == "{{query}}"
    assert changed["empty_result"]["query"] == "c++ & tools"


@pytest.mark.parametrize(
    "url, heading",
    [
        ("https://elsewhere.example/search?q=green+tea", "Search for 'green tea'"),
        ("https://registry.example/search?q=green+tea&q=older", "Search for 'green tea'"),
        ("https://registry.example/search?q=green+tea&other=green+tea", "Search for 'green tea'"),
        (RESULT, "Search for 'old query'"),
        (RESULT, "green tea"),
    ],
)
def test_no_binding_from_unobserved_or_ambiguous_query_identity(url, heading):
    assert ground_empty_result_recipe(START, url, heading, "green tea", "{{query}}", MESSAGE) is None


def test_opt_in_does_not_mark_a_required_result_or_a_preseeded_query_as_empty():
    explored = _explored()
    explored.commands[0].expects_nonempty = True
    with pytest.raises(ExploreContractError, match="零结果约定"):
        _bind_explicit_empty_result(explored, {2: _observation()}, MESSAGE)
    assert "empty_result" not in explored.actions[2].extract_target
    assert ground_empty_result_recipe(
        RESULT, RESULT, "Search for 'green tea'", "green tea", "{{query}}", MESSAGE,
    ) is None


def test_empty_outcome_requires_exact_query_and_summary_and_cannot_coexist_with_a_collection():
    explored = _explored()
    _bind_explicit_empty_result(explored, {2: _observation()}, MESSAGE)
    recipe = {**explored.actions[2].extract_target["empty_result"], "query": "c++ & tools"}
    page = "https://registry.example/search?q=c%2B%2B+%26+tools"
    state = {"heading": "Search for 'c++ & tools'", "collections": 0, "busy": False, "messages": [MESSAGE]}
    assert observed_search_outcome({"url": page, "main_result_context": state}, recipe) == "empty"
    for change in ({"collections": 1}, {"busy": True}, {"messages": []}, {"messages": [MESSAGE, MESSAGE]}):
        assert observed_search_outcome({"url": page, "main_result_context": {**state, **change}}, recipe) is None
    assert observed_search_outcome({"url": RESULT, "main_result_context": state}, recipe) is None
