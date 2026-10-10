import json
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.config import get_config
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer

DOMAIN = "params.example.test"
URL = f"https://{DOMAIN}/form"


@pytest.fixture
def adapter(tmp_home, clean_env, no_llm, monkeypatch):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")

    def generate(mode):
        value = "{{name}}" if mode == "auto" else "recorded"
        args = [{"name": "name", "default": "Ada", "action_index": 0}] if mode == "default" else []
        result = ExploreResult(
            pages=[PageInfo(URL, "Form")],
            actions=[
                ActionStep("type", URL, target_ref="8", target_name="Name", value=value),
                ActionStep("extract", URL, selector="output", extract_mode="list", fields_map={"name": ""}),
            ],
            commands=[CommandSuggestion("read-name", "Read name", args, [0, 1])],
        )
        save_adapter(DOMAIN, AdapterGenerator().generate(result, DOMAIN), {"source_url": URL}, result)
        return get_config().adapters_dir / DOMAIN

    return generate


async def _invoke(entrypoint, params, dry_run=False):
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            return await sdk.execute(DOMAIN, "read-name", params=params, dry_run=dry_run), None
        server = APIServer()
        server._sdk = sdk
        async with TestClient(TestServer(server._build_app())) as client:
            response = await client.post(
                "/execute", json={"domain": DOMAIN, "command": "read-name", "params": params, "dry_run": dry_run},
            )
            return await response.json(), response.status


@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("mode", ["default", "auto", "fixed"])
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("params", [
    {"nmae": "private-value-do-not-reflect"},
    {"name": "Grace", "nmae": "private-value-do-not-reflect"},
    {7: "private-value-do-not-reflect"},
])
async def test_unknown_names_stop_before_browser(adapter, monkeypatch, entrypoint, mode, dry_run, params):
    directory = adapter(mode)
    before = {name: (directory / name).read_bytes() for name in ("commands.py", "metadata.json")}
    connect = AsyncMock()
    replay = AsyncMock()
    load_session = AsyncMock()
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", connect)
    monkeypatch.setattr("cliany_site.session.load_session", load_session)
    monkeypatch.setattr("cliany_site.action_runtime.execute_action_steps", replay)
    payload, status = await _invoke(entrypoint, params, dry_run)
    assert payload["success"] is False, payload
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    allowed = ["name"] if mode != "fixed" else []
    unknown = sorted(str(name) for name in params if name not in allowed)
    assert payload["error"]["details"] == {"unknown_params": unknown, "allowed_params": allowed}
    assert "private-value-do-not-reflect" not in json.dumps(payload)
    assert status is None if entrypoint == "sdk" else status == 400
    connect.assert_not_awaited()
    load_session.assert_not_awaited()
    replay.assert_not_awaited()
    assert before == {name: (directory / name).read_bytes() for name in before}


@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("mode,params,expected", [
    ("default", None, "Ada"), ("default", {}, "Ada"), ("default", {"name": "Grace"}, "Grace"),
    ("auto", {"name": "Grace"}, "Grace"), ("fixed", None, "recorded"), ("fixed", {}, "recorded"),
])
async def test_declared_inputs_and_defaults_still_replay(adapter, monkeypatch, entrypoint, mode, params, expected):
    adapter(mode)
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", AsyncMock())
    monkeypatch.setattr("cliany_site.session.load_session", AsyncMock())

    async def replay(_session, actions, **kwargs):
        from cliany_site.action_runtime import substitute_parameters

        resolved = substitute_parameters(actions, kwargs["params"])
        assert resolved[1]["value"] == expected
        kwargs["extraction_results"].append({
            "step_index": 2, "extract_mode": "list", "fields": {"name": ""}, "data": [{"name": expected}],
        })

    monkeypatch.setattr("cliany_site.action_runtime.execute_action_steps", replay)
    payload, status = await _invoke(entrypoint, params)
    assert payload["success"] is True, payload
    assert payload["data"]["results"][0]["data"] == [{"name": expected}]
    assert status is None if entrypoint == "sdk" else status == 200
