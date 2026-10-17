import ast
import json
from dataclasses import asdict
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.codegen.merger import AdapterMerger
from cliany_site.codegen.params import ParameterBindingError, build_param_overrides
from cliany_site.codegen.templates import render_command_block, render_command_block_v2
from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import _apply_partition_repair, _invalid_command_parameter_bindings
from cliany_site.explorer.models import ActionStep, CommandSuggestion, exploration_history
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer


def _inputs():
    return [ActionStep("type", "https://example.test", target_ref="1", target_name="Search",
                       target_role="textbox", value="Alpha") for _ in range(3)]


def test_explicit_binding_does_not_spread_to_fixed_or_later_matching_inputs():
    actions = _inputs()
    assert build_param_overrides([{"name": "query", "action_index": 1}], [0, 1, 2], actions) == {1: "{{query}}"}


def test_one_argument_can_explicitly_bind_multiple_owned_inputs_without_broadcast():
    actions = _inputs()
    assert build_param_overrides([{"name": "query", "action_indices": [0, 2]}], [0, 1, 2], actions) == {
        0: "{{query}}", 2: "{{query}}",
    }


@pytest.mark.parametrize("binding", [
    {"action_indices": []}, {"action_indices": [0, 0]}, {"action_indices": [False]},
    {"action_indices": ["0"]}, {"action_indices": [None]}, {"action_indices": [3]},
    {"action_indices": [1]}, {"action_indices": "0"}, {"action_index": 0, "action_indices": [0]},
])
def test_multi_binding_requires_unambiguous_owned_integer_indices(binding):
    with pytest.raises(ValueError):
        build_param_overrides([{"name": "query", **binding}], [0, 2], _inputs())


def test_multi_binding_does_not_accept_non_value_actions_or_clobbered_arguments():
    actions = _inputs()
    actions[2].action_type = "click"
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "query", "action_indices": [0, 2]}], [0, 1, 2], actions)
    with pytest.raises(ParameterBindingError):
        build_param_overrides([{"name": "query", "action_indices": [0, 1]},
                               {"name": "other", "action_indices": [0, 1]}], [0, 1], actions)


def test_matching_default_is_not_authority_to_choose_or_change_multiple_scopes():
    with pytest.raises(ParameterBindingError) as caught:
        build_param_overrides([{"name": "query", "default": "Alpha"}], [0, 1], _inputs())
    assert caught.value.reason == "ambiguous_default"
    plan = {"done": True, "commands": [{"args": [{"name": "query", "default": "Alpha"}],
                                         "action_steps": [0, 1]}]}
    failures = _invalid_command_parameter_bindings(plan, [], _inputs()[:2], set())
    assert len(failures) == 1 and failures[0]["parameter_name"] == "query"


def test_partition_repair_cannot_move_one_of_a_multi_bound_parameters_inputs():
    commands = [{"name": "first", "args": [{"name": "query", "action_indices": [0, 2]}], "action_steps": [0, 2]},
                {"name": "second", "action_steps": [1]}]
    repair = {"actions": [], "done": True, "commands": [
        {"name": "first", "action_steps": [0, 1]}, {"name": "second", "action_steps": [2]},
    ]}
    with pytest.raises(ExploreContractError):
        _apply_partition_repair(commands, repair, 3)
    assert commands[0]["args"][0]["action_indices"] == [0, 2]


def test_merge_rebases_multi_bindings_from_complete_gapped_mapping_without_mutation():
    args = [{"name": "query", "action_indices": [2, 4]}]
    commands = [{"name": "prefix", "actions": [asdict(_inputs()[0])], "action_steps": [0], "args": []},
                {"name": "both", "actions": [asdict(action) for action in _inputs()[:2]],
                 "action_steps": [2, 4], "args": args}]
    rebuilt = AdapterMerger("example.test")._rebuild_explore_result(commands)
    assert rebuilt.commands[1].args[0]["action_indices"] == [1, 2]
    assert args[0]["action_indices"] == [2, 4]


def test_history_keeps_full_original_multi_binding_as_a_deep_snapshot():
    command = CommandSuggestion("fill", "Fill both inputs", [{"name": "query", "action_indices": [0, 2]}], [0, 2])
    history = exploration_history(_inputs(), [command])
    command.args[0]["action_indices"][0] = 99
    assert history["commands"][0]["args"][0]["action_indices"] == [0, 2]
    assert history["commands"][0]["description"] == "Fill both inputs"


@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("binding", [
    {"default": "Alpha"}, {"action_indices": [2, False]}, {"action_indices": [2, 99]},
    {"action_indices": [2, 2]}, {"action_indices": []},
])
async def test_invalid_legacy_binding_returns_static_error_before_browser(
    binding, entrypoint, dry_run, tmp_home, monkeypatch,
):
    directory = get_config().adapters_dir / "example.test"
    directory.mkdir(parents=True)
    raw = {"schema_version": 1, "commands": [{"name": "fill", "action_steps": [2, 4],
           "args": [{"name": "query", **binding}], "actions": [asdict(action) for action in _inputs()[:2]]}]}
    (directory / "metadata.json").write_text(json.dumps(raw))
    connect = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", connect)
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            payload = await sdk.execute("example.test", "fill", params={"query": "secret-input"}, dry_run=dry_run)
        else:
            api = APIServer()
            api._sdk = sdk
            async with TestClient(TestServer(api._build_app())) as client:
                response = await client.post("/execute", json={
                    "domain": "example.test", "command": "fill", "params": {"query": "secret-input"},
                    "dry_run": dry_run,
                })
                assert response.status == 422 and response.content_type == "application/json"
                payload = await response.json()
    assert payload["success"] is False and payload["error"]["code"] == "E_VERIFY_STATIC"
    assert payload["error"]["details"]["reason"] in {"ambiguous_default", "invalid_ownership"}
    assert "secret-input" not in json.dumps(payload)
    connect.assert_not_awaited()


async def test_sdk_rebases_valid_multi_bindings_across_probe_gaps(tmp_home, monkeypatch):
    directory = get_config().adapters_dir / "example.test"
    directory.mkdir(parents=True)
    raw = {"schema_version": 1, "commands": [{"name": "fill", "action_steps": [2, 4],
           "args": [{"name": "query", "action_indices": [2, 4]}],
           "actions": [asdict(action) for action in _inputs()[:2]]}]}
    (directory / "metadata.json").write_text(json.dumps(raw))
    replay = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", AsyncMock())
    monkeypatch.setattr("cliany_site.session.load_session", AsyncMock())
    monkeypatch.setattr("cliany_site.action_runtime.execute_action_steps", replay)
    async with ClanySite() as sdk:
        payload = await sdk.execute("example.test", "fill", params={"query": "Gamma"})
    assert payload["success"] is True
    assert [action["value"] for action in replay.call_args.args[1]] == ["{{query}}", "{{query}}"]
    assert replay.call_args.kwargs["params"] == {"query": "Gamma"}


@pytest.mark.parametrize("mapping", [[2, 2], [2, False], [2], [2, "4"]])
async def test_sdk_rejects_incomplete_or_aliased_original_index_mapping(mapping, tmp_home, monkeypatch):
    directory = get_config().adapters_dir / "example.test"
    directory.mkdir(parents=True)
    raw = {"schema_version": 1, "commands": [{"name": "fill", "action_steps": mapping,
           "args": [{"name": "query", "action_indices": [2, 4]}],
           "actions": [asdict(action) for action in _inputs()[:2]]}]}
    (directory / "metadata.json").write_text(json.dumps(raw))
    connect = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", connect)
    async with ClanySite() as sdk:
        payload = await sdk.execute("example.test", "fill", params={"query": "Gamma"})
    assert payload["success"] is False and payload["error"]["code"] == "E_VERIFY_STATIC"
    assert payload["error"]["details"] == {"reason": "invalid_ownership"}
    connect.assert_not_awaited()


@pytest.mark.parametrize("renderer", [render_command_block, render_command_block_v2])
@pytest.mark.parametrize("kind", ["click", "submit", "navigate", "type"])
def test_renderers_preserve_order_and_multiplicity_of_recorded_actions(renderer, kind):
    repeated = ActionStep(kind, "https://example.test", target_ref="1", target_name="Continue",
                          target_role="button", target_url="https://example.test", value="fixed")
    actions = [repeated, repeated, ActionStep("click", "https://example.test", target_ref="2"), repeated]
    command = CommandSuggestion("run-steps", "Run recorded steps", [], [0, 1, 2, 3])
    code = renderer(command, actions, 0)
    emitted = []
    for node in ast.walk(ast.parse(code)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "loads"
                and node.args and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str) and node.args[0].value.startswith("[")):
            emitted.extend(json.loads(node.args[0].value))
    assert [step["type"] for step in emitted] == [kind, kind, "click", kind]
