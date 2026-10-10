import json
from http import HTTPStatus
from unittest.mock import AsyncMock

import httpx
import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.config import get_config
from cliany_site.errors import LlmUnavailableError
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer

URL = "https://sdk-errors.example.test/start"
PRIVATE_MARKER = "private-fixture-token"


@pytest.fixture
def isolated_sdk(tmp_home, clean_env, monkeypatch):
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "config"))
    monkeypatch.chdir(tmp_home)
    monkeypatch.setattr("cliany_site.explorer.engine._load_dotenv", lambda: None)


async def _call(entrypoint, *, force=False):
    async with ClanySite() as sdk:
        if entrypoint == "sdk":
            return await sdk.explore(URL, "read result", force=force), None
        server = APIServer()
        server._sdk = sdk
        async with TestClient(TestServer(server._build_app())) as client:
            response = await client.post("/explore", json={"url": URL, "workflow": "read result", "force": force})
            assert response.content_type == "application/json"
            return await response.json(), response.status


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("status,retryable", [
    (401, False), (403, False), (400, False), (422, False),
    (429, True), (502, True), (None, True),
])
async def test_typed_provider_error_is_safe_structured_result(
    isolated_sdk, monkeypatch, caplog, entrypoint, status, retryable,
):
    failure = LlmUnavailableError(
        f"Bad Gateway {PRIVATE_MARKER} https://private.invalid/endpoint", status_code=status, retryable=retryable,
    )
    monkeypatch.setattr("cliany_site.explorer.engine.WorkflowExplorer.explore", AsyncMock(side_effect=failure))
    payload, http_status = await _call(entrypoint)
    assert payload["success"] is False
    assert payload["data"] is None
    assert "ok" not in payload
    assert payload["error"]["code"] == ("E_LLM_AUTH_FAILED" if status in {401, 403} else "E_LLM_UNAVAILABLE")
    assert payload["error"]["details"] == {"retryable": retryable, "status_code": status, "phase": "llm_invoke"}
    assert payload["error"]["fix"]
    assert http_status == (503 if entrypoint == "http" else None)
    assert PRIVATE_MARKER not in json.dumps(payload) + caplog.text
    assert "private.invalid" not in json.dumps(payload) + caplog.text
    assert not (get_config().adapters_dir / "sdk-errors.example.test" / "commands.py").exists()
    assert not (get_config().adapters_dir / "sdk-errors.example.test" / "metadata.json").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
async def test_provider_failure_keeps_existing_files_even_with_force(isolated_sdk, monkeypatch, entrypoint):
    directory = get_config().adapters_dir / "sdk-errors.example.test"
    directory.mkdir(parents=True)
    commands = directory / "commands.py"
    metadata = directory / "metadata.json"
    commands.write_text("# existing fixture\n")
    metadata.write_text('{"source_url": "https://sdk-errors.example.test/old"}\n')
    before = commands.read_bytes(), metadata.read_bytes()
    monkeypatch.setattr("cliany_site.explorer.engine.WorkflowExplorer.explore", AsyncMock(
        side_effect=LlmUnavailableError(PRIVATE_MARKER, status_code=401, retryable=False),
    ))
    payload, _status = await _call(entrypoint, force=True)
    assert payload["success"] is False
    assert payload["error"]["code"] == "E_LLM_AUTH_FAILED"
    assert (commands.read_bytes(), metadata.read_bytes()) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
@pytest.mark.parametrize("scenario,expected_requests,status", [
    ("auth", 1, 401), ("forbidden", 1, 403), ("rejected", 1, 400),
    ("limited", 3, 429), ("gateway", 3, 502), ("timeout", 3, None),
    ("recovery", 2, None),
])
async def test_actual_sdk_transport_through_error_boundary(
    isolated_sdk, monkeypatch, caplog, entrypoint, scenario, expected_requests, status,
):
    from langchain_openai import ChatOpenAI

    from cliany_site.explorer.engine import _invoke_llm_with_retry
    from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo

    requests = []

    def respond(request):
        requests.append(request)
        assert request.headers["authorization"] == "Bearer test-key"
        if scenario == "timeout":
            raise httpx.ReadTimeout(PRIVATE_MARKER, request=request)
        if scenario == "recovery" and len(requests) > 1:
            return httpx.Response(200, json={
                "id": "fixture", "object": "chat.completion", "created": 0, "model": "fixture-json",
                "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "{}"}}],
            })
        response_status = HTTPStatus.UNAUTHORIZED if scenario == "auth" else 429 if scenario == "recovery" else status
        return httpx.Response(response_status, json={"error": {"message": f"Bad Gateway {PRIVATE_MARKER}"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as client:
        model = ChatOpenAI(
            api_key="test-key", model="fixture-json", max_retries=0, timeout=120, http_async_client=client,
        )

        async def explore(*_args, **_kwargs):
            await _invoke_llm_with_retry(model, "fixture JSON prompt", max_attempts=3, base_delay=0)
            return ExploreResult(
                pages=[PageInfo(URL, "Fixture")],
                actions=[ActionStep("extract", URL, selector="#result", extract_mode="text")],
                commands=[CommandSuggestion("read-result", "Read fixture", [], [0])],
                explore_model="fixture-json",
            )

        monkeypatch.setattr("cliany_site.explorer.engine.WorkflowExplorer.explore", explore)
        payload, http_status = await _call(entrypoint)

    assert len(requests) == expected_requests
    assert PRIVATE_MARKER not in json.dumps(payload) + caplog.text
    directory = get_config().adapters_dir / "sdk-errors.example.test"
    if scenario == "recovery":
        assert payload["success"] is True
        assert payload["data"]["adapter_mode"] == "created"
        assert http_status == (200 if entrypoint == "http" else None)
        assert (directory / "commands.py").exists()
    else:
        assert payload["success"] is False
        assert payload["error"]["code"] == ("E_LLM_AUTH_FAILED" if status in {401, 403} else "E_LLM_UNAVAILABLE")
        assert payload["error"]["details"] == {
            "retryable": status not in {400, 401, 403}, "status_code": status, "phase": "llm_invoke",
        }
        assert http_status == (503 if entrypoint == "http" else None)
        assert not (directory / "commands.py").exists()
        assert not (directory / "metadata.json").exists()
