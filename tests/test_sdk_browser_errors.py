import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.errors import CdpError
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer

DOMAIN = "browser-errors.example.test"
URL = f"https://{DOMAIN}/start"
PRIVATE = "private-endpoint-or-response-do-not-reflect"
METHODS = ["execute", "login", "save_session", "navigate", "get_page_info"]


@pytest.fixture
def adapter(tmp_home, clean_env, no_llm, monkeypatch):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    result = ExploreResult(
        pages=[PageInfo(URL, "Start")],
        actions=[ActionStep("navigate", URL, target_url=URL)],
        commands=[CommandSuggestion("visit", "Visit", [], [0])],
    )
    save_adapter(DOMAIN, AdapterGenerator().generate(result, DOMAIN), {"source_url": URL}, result)


async def _call(sdk, method):
    if method == "execute":
        return await sdk.execute(DOMAIN, "visit")
    if method in {"login", "navigate"}:
        return await getattr(sdk, method)(URL)
    if method == "save_session":
        return await sdk.save_session(DOMAIN)
    return await sdk.get_page_info()


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("failure", ["probe", CdpError, ConnectionError, TimeoutError])
async def test_expected_acquisition_errors_are_safe_envelopes(adapter, monkeypatch, method, failure):
    cdp = SimpleNamespace(
        check_available=AsyncMock(return_value=failure != "probe"),
        connect=AsyncMock(side_effect=None if failure == "probe" else failure(PRIVATE)),
    )
    monkeypatch.setattr(ClanySite, "_ensure_cdp", AsyncMock(return_value=cdp))
    replay = AsyncMock()
    capture = AsyncMock()
    save = AsyncMock()
    monkeypatch.setattr("cliany_site.action_runtime.execute_action_steps", replay)
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    monkeypatch.setattr("cliany_site.session.save_session", save)
    sdk = ClanySite()
    result = await _call(sdk, method)
    assert result["success"] is False
    assert result["error"]["code"] == "CDP_UNAVAILABLE"
    assert result["error"]["details"] == {"phase": "browser_connect"}
    assert "doctor --json" in result["error"]["fix"]
    assert PRIVATE not in json.dumps(result)
    assert sdk._session is None
    cdp.check_available.assert_awaited_once()
    replay.assert_not_awaited()
    capture.assert_not_awaited()
    save.assert_not_awaited()
    if failure == "probe":
        cdp.connect.assert_not_awaited()
    else:
        cdp.connect.assert_awaited_once()


@pytest.mark.parametrize("route", ["/execute", "/login"])
@pytest.mark.parametrize("failure", [CdpError, ConnectionError, TimeoutError])
async def test_actual_http_returns_json_503(adapter, monkeypatch, route, failure):
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", AsyncMock(side_effect=failure(PRIVATE)))
    api = APIServer()
    async with TestClient(TestServer(api._build_app())) as client:
        body = {"domain": DOMAIN, "command": "visit"} if route == "/execute" else {"url": URL}
        response = await client.post(route, json=body)
        assert response.status == 503
        assert response.content_type == "application/json"
        result = await response.json()
        assert result["success"] is False and result["error"]["code"] == "CDP_UNAVAILABLE"
        assert result["error"]["details"] == {"phase": "browser_connect"}
        assert PRIVATE not in json.dumps(result)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("failure", [RuntimeError, asyncio.CancelledError])
async def test_unknown_errors_and_cancellation_are_not_mislabeled(adapter, monkeypatch, method, failure):
    monkeypatch.setattr(ClanySite, "_ensure_browser_session", AsyncMock(side_effect=failure(PRIVATE)))
    with pytest.raises(failure):
        await _call(ClanySite(), method)
