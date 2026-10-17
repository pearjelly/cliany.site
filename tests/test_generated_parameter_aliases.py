import json
from dataclasses import asdict
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.action_runtime import substitute_parameters
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer


@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("raw_name,alias,value", [
    ("search-term", "search_term", "Gamma"),
    ("ctx", "ctx_2", "Gamma"),
    ("json_mode", "json_mode_2", "Gamma"),
    ("1term", "arg_1term", "Gamma"),
    ("ctx", "ctx_2", 0),
    ("ctx", "ctx_2", False),
])
@pytest.mark.parametrize("use_default", [False, True])
async def test_generated_sdk_and_http_substitute_same_alias_as_cli(
    raw_name, alias, value, entrypoint, use_default, tmp_home, monkeypatch,
):
    directory = get_config().adapters_dir / "example.test"
    directory.mkdir(parents=True)
    argument = {"name": raw_name, "required": True}
    if use_default:
        argument["default"] = value
    action = ActionStep("type", "https://example.test", target_name="Search", target_role="textbox",
                        value="{{" + alias + "}}")
    metadata = {"schema_version": 1, "commands": [{"name": "fill", "args": [argument],
                "actions": [asdict(action)], "action_steps": [0]}]}
    (directory / "metadata.json").write_text(json.dumps(metadata))
    replay = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", AsyncMock())
    monkeypatch.setattr("cliany_site.session.load_session", AsyncMock())
    monkeypatch.setattr("cliany_site.action_runtime.execute_action_steps", replay)
    params = {} if use_default else {raw_name: value}
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            payload = await sdk.execute("example.test", "fill", params=params)
        else:
            api = APIServer()
            api._sdk = sdk
            async with TestClient(TestServer(api._build_app())) as client:
                response = await client.post("/execute", json={
                    "domain": "example.test", "command": "fill", "params": params,
                })
                assert response.status == 200
                payload = await response.json()
    assert payload["success"] is True
    effective = substitute_parameters(replay.call_args.args[1], replay.call_args.kwargs["params"])
    assert effective[0]["value"] == str(value)
    assert params == ({} if use_default else {raw_name: value})


@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("raw_name,alias", [("search-term", "search_term"), ("json_mode", "json_mode_2")])
async def test_internal_alias_is_not_an_extra_public_parameter(raw_name, alias, entrypoint, tmp_home, monkeypatch):
    directory = get_config().adapters_dir / "example.test"
    directory.mkdir(parents=True)
    action = ActionStep("type", "https://example.test", value="{{" + alias + "}}")
    (directory / "metadata.json").write_text(json.dumps({"schema_version": 1, "commands": [{
        "name": "fill", "args": [{"name": raw_name}], "action_steps": [0], "actions": [asdict(action)],
    }]}))
    connect = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", connect)
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            payload = await sdk.execute("example.test", "fill", params={alias: "private-value"})
        else:
            api = APIServer()
            api._sdk = sdk
            async with TestClient(TestServer(api._build_app())) as client:
                response = await client.post("/execute", json={
                    "domain": "example.test", "command": "fill", "params": {alias: "private-value"},
                })
                assert response.status == 400
                payload = await response.json()
    assert payload["success"] is False and payload["error"]["code"] == "E_INVALID_PARAM"
    assert payload["error"]["details"] == {"unknown_params": [alias], "allowed_params": [raw_name]}
    assert "private-value" not in json.dumps(payload)
    connect.assert_not_awaited()
