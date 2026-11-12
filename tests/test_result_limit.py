import json
import types
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.browser.selector import MAIN_RESULT_LIST_ROOT, MAIN_RESULT_LIST_SCOPE
from cliany_site.codegen.collection_scope import CollectionScopeError
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.codegen.merger import AdapterMerger
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.sdk import ClanySite

DOMAIN = "registry.example"
SOURCE = f"https://{DOMAIN}/"


def _workflow():
    command = CommandSuggestion(
        "search-crates", "Search crates", [{"name": "query", "required": True, "action_index": 0}], [0, 1, 2],
        expects_nonempty=False, result_limit=True,
    )
    return ExploreResult(
        pages=[PageInfo(SOURCE, "Registry")],
        actions=[
            ActionStep("type", SOURCE, value="example", target_role="searchbox", target_name="Search"),
            ActionStep("click", SOURCE, target_role="button", target_name="Search"),
            ActionStep(
                "extract", SOURCE, selector=MAIN_RESULT_LIST_ROOT, extract_mode="list", fields_map={"title": "a"},
                extract_target={"role": "list", "scope": MAIN_RESULT_LIST_SCOPE},
            ),
        ],
        commands=[command],
    )


@pytest.mark.parametrize(
    "titles, expected_success", [(["first", "second", "third"], True), (["first", "second", ""], False), ([], True)],
)
def test_generated_cli_limits_only_the_output_not_its_quality_check(titles, expected_success):
    code = AdapterGenerator().generate(_workflow(), DOMAIN)
    module = types.ModuleType("limited_adapter")
    exec(code, module.__dict__)  # noqa: S102 - test the actual generated Click command
    rows = [{"title": value} for value in titles]

    def replay(action_steps, source_url, domain):
        assert action_steps[0]["value"] == "changed" and len(action_steps) == 3
        return [
            {"ok": True, "command": "browser type"}, {"ok": True, "command": "browser click"},
            {"ok": True, "command": "browser extract", "data": {"mode": "list", "content": rows}},
        ]

    module.execute_steps_via_atoms = replay
    result = CliRunner().invoke(module.cli, ["search-crates", "--query", "changed", "--limit", "2", "--json"])
    assert result.exit_code == (0 if expected_success else 1), result.output
    payload = json.loads(result.output)
    assert payload["ok"] is expected_success
    assert payload["data"]["results"][-1]["data"]["content"] == rows[:2]
    assert payload["data"]["quality"]["result_limit"] == {
        "requested": 2, "inspected_rows": len(rows), "returned_rows": len(rows[:2]), "truncated": len(rows) > 2,
    }
    if not expected_success:
        assert payload["error"]["code"] == "E_EMPTY_RESULT"
        assert payload["data"]["quality"]["extracts"][0]["field_blank_rows"] == {"title": [3]}


@pytest.mark.asyncio
async def test_generated_sdk_limit_is_validated_before_connecting_and_not_used_as_page_input(tmp_home):
    workflow = _workflow()
    save_adapter(DOMAIN, AdapterGenerator().generate(workflow, DOMAIN), explore_result=workflow)
    with patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()) as connect:
        for invalid in (None, True, "2", 0, 101):
            outcome = await ClanySite().execute(DOMAIN, "search-crates", params={"query": "changed", "limit": invalid})
            assert outcome["error"]["code"] == "E_INVALID_PARAM"
        connect.assert_not_awaited()

    async def replay(session, actions, **kwargs):
        assert kwargs["params"] == {"query": "changed"}
        kwargs["extraction_results"].append({
            "step_index": 3, "extract_mode": "list", "fields": {"title": "a"},
            "data": [{"title": "first"}, {"title": "second"}, {"title": "third"}],
        })

    with (
        patch.object(ClanySite, "_ensure_browser_session", new=AsyncMock()),
        patch("cliany_site.session.load_session", new=AsyncMock()),
        patch("cliany_site.action_runtime.execute_action_steps", side_effect=replay),
    ):
        result = await ClanySite().execute(DOMAIN, "search-crates", params={"query": "changed", "limit": 2})
    assert result["success"] is True, result
    assert result["data"]["results"][0]["data"] == [{"title": "first"}, {"title": "second"}]
    assert result["data"]["quality"]["result_limit"] == {
        "requested": 2, "inspected_rows": 3, "returned_rows": 2, "truncated": True,
    }


def test_invalid_cli_limit_does_not_run_browser_steps():
    module = types.ModuleType("limited_adapter")
    exec(AdapterGenerator().generate(_workflow(), DOMAIN), module.__dict__)  # noqa: S102

    def replay(*args):
        pytest.fail("invalid limit entered browser replay")

    module.execute_steps_via_atoms = replay
    for invalid in ("0", "101", "1.5"):
        result = CliRunner().invoke(module.cli, ["search-crates", "--query", "changed", "--limit", invalid])
        assert result.exit_code == 2 and "Invalid value for '--limit'" in result.output


@pytest.mark.parametrize("case", ["not_terminal", "not_list", "multiple", "option_collision", "sdk_name_collision"])
def test_refuses_ambiguous_limit_contracts(case):
    workflow = _workflow()
    command = workflow.commands[0]
    if case == "not_terminal":
        command.action_steps = [0, 2, 1]
    elif case == "not_list":
        workflow.actions[2].extract_mode = "text"
    elif case == "multiple":
        workflow.actions.append(workflow.actions[2])
        command.action_steps.append(3)
    elif case == "option_collision":
        command.args[0]["option"] = "--limit"
    else:
        command.args[0].update(name="limit", option="--site-limit")
    with pytest.raises(CollectionScopeError, match="--limit"):
        AdapterGenerator().generate(workflow, DOMAIN)


def test_result_limit_survives_rebuild_without_becoming_a_page_parameter(tmp_home):
    workflow = _workflow()
    merger = AdapterMerger(DOMAIN)
    merged = merger.merge_commands(existing=[], new_commands=workflow.commands, new_actions=workflow.actions)
    merger.save_merged(merged)
    metadata = json.loads((get_config().adapters_dir / DOMAIN / "metadata.json").read_text())
    rebuilt = merger._rebuild_explore_result(metadata["commands"])
    assert rebuilt.commands[0].result_limit is True
    assert [arg["name"] for arg in rebuilt.commands[0].args] == ["query"]
