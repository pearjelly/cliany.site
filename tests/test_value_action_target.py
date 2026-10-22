import json
from dataclasses import asdict
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.codegen.generator import AdapterGenerator
from cliany_site.codegen.params import ParameterBindingError, value_action_on_noneditable_link
from cliany_site.codegen.templates import render_command_block, render_command_block_v2
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer


@pytest.mark.parametrize(("kind", "role", "attributes", "invalid"), [
    ("type", "link", {}, True), ("select", "link", {}, True),
    ("type", " Link ", {"contenteditable": "false"}, True),
    ("type", "link", {"contenteditable": "true"}, False),
    ("type", "link", {"contenteditable": ""}, False),
    ("type", "link", {"contenteditable": "plaintext-only"}, False),
    ("select", "link", {"contenteditable": "true"}, True),
    ("click", "link", {}, False), ("type", "textbox", {}, False), ("type", "", {}, False),
])
def test_known_link_value_target_compatibility(kind, role, attributes, invalid):
    assert value_action_on_noneditable_link(kind, role, attributes) is invalid


def _actions():
    return [ActionStep("type", "https://example.test", target_ref="1", target_name="Full Search",
                       target_role="link", target_attributes={"href": "/search"}, value="placeholder"),
            ActionStep("type", "https://example.test/search", target_ref="2", target_name="Query",
                       target_role="textbox", value="Alpha")]


@pytest.mark.parametrize("renderer", [render_command_block, render_command_block_v2])
@pytest.mark.parametrize("arguments", [[], [{"name": "query", "required": True, "action_index": 1}]])
def test_renderers_refuse_even_unbound_link_value_actions(renderer, arguments):
    command = CommandSuggestion("search", "Search", arguments, [0, 1])
    with pytest.raises(ParameterBindingError) as caught:
        renderer(command, _actions(), 0)
    assert caught.value.reason == "value_target_incompatible"
    assert caught.value.action_index == 0
    assert "placeholder" not in str(caught.value)


def test_generator_cannot_publish_a_recorded_link_placeholder():
    command = CommandSuggestion("search", "Search", [{"name": "query", "action_index": 1}], [0, 1])
    with pytest.raises(ParameterBindingError, match="不可输入"):
        AdapterGenerator().generate(ExploreResult(actions=_actions(), commands=[command]), "example.test")


@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("dry_run", [False, True])
async def test_legacy_link_value_step_fails_static_before_browser(entrypoint, dry_run, tmp_home, monkeypatch):
    directory = get_config().adapters_dir / "example.test"
    directory.mkdir(parents=True)
    metadata = {"schema_version": 1, "commands": [{"name": "search", "action_steps": [2, 4],
                "args": [{"name": "query", "action_index": 4}], "actions": [asdict(action) for action in _actions()]}]}
    (directory / "metadata.json").write_text(json.dumps(metadata))
    connect = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", connect)
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            payload = await sdk.execute("example.test", "search", params={"query": "private-input"}, dry_run=dry_run)
        else:
            api = APIServer()
            api._sdk = sdk
            async with TestClient(TestServer(api._build_app())) as client:
                response = await client.post("/execute", json={
                    "domain": "example.test", "command": "search", "params": {"query": "private-input"},
                    "dry_run": dry_run,
                })
                assert response.status == 422
                payload = await response.json()
    assert payload["success"] is False and payload["error"]["code"] == "E_VERIFY_STATIC"
    assert payload["error"]["details"] == {"reason": "value_target_incompatible"}
    assert "private-input" not in json.dumps(payload)
    connect.assert_not_awaited()
