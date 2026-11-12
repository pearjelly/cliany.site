import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import langchain_openai
import pytest
from aiohttp.test_utils import TestClient, TestServer
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands.doctor import _run_llm_live_check
from cliany_site.config import get_config
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer

MALFORMED_PROBE = "fixture-plain-text-not-json"


@pytest.mark.asyncio
@pytest.mark.parametrize(("content", "reason"), [
    ('{"status":"ok"}', None),
    ('```json\n{"status":"ok"}\n```', None),
    (MALFORMED_PROBE, "llm_invalid_json"),
    ("[]", "llm_invalid_shape"),
])
async def test_openai_preflight_checks_json_mode_response(tmp_home, clean_env, monkeypatch, content, reason):
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["response_format"] == {"type": "json_object"}
        if not any("json" in message["content"].lower() for message in payload["messages"]):
            return httpx.Response(400, json={"error": {
                "message": "messages must contain json for JSON mode",
                "type": "invalid_request_error",
            }})
        return httpx.Response(200, json={
            "id": "chatcmpl-preflight",
            "object": "chat.completion",
            "created": 0,
            "model": "test-model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": content,
            }}],
        })

    monkeypatch.delenv("CLIANY_QA_OFFLINE", raising=False)
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLIANY_OPENAI_BASE_URL", "https://preflight.invalid/v1")
    monkeypatch.setenv("CLIANY_OPENAI_MODEL", "test-model")
    monkeypatch.setattr("cliany_site.explorer.engine._load_dotenv", lambda: None)
    original = langchain_openai.ChatOpenAI
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(langchain_openai, "ChatOpenAI", lambda **kwargs: original(
            **kwargs, http_async_client=client,
        ))
        result = await _run_llm_live_check(True, "openai")

    assert len(requests) == 1
    assert result["details"]["phase"] == "llm_preflight"
    if reason is None:
        assert result["status"] == "ok"
    else:
        assert result["status"] == "warning"
        assert result["details"]["error_code"] == "E_LLM_UNAVAILABLE"
        assert result["details"]["reason"] == reason
        assert result["details"]["retryable"] is False
        assert content not in result["details"]["message"]


@pytest.fixture
def malformed_live_probe(tmp_home, clean_env, monkeypatch):
    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("cliany_site.explorer.engine._load_dotenv", lambda: None)
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", object)
    invoke = AsyncMock(return_value=SimpleNamespace(content=MALFORMED_PROBE))
    monkeypatch.setattr("cliany_site.explorer.engine._invoke_llm_with_retry", invoke)
    cdp = SimpleNamespace(check_available=AsyncMock(return_value=True))
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", lambda *args, **kwargs: cdp)
    monkeypatch.setattr(ClanySite, "_ensure_cdp", AsyncMock(return_value=cdp))
    get_config().adapters_dir.mkdir(parents=True, exist_ok=True)
    return invoke


def _assert_strict_probe_blocked(payload, invoke):
    assert payload["error"]["code"] == "E_LLM_UNAVAILABLE"
    summary = payload["error"]["details"]["summary"]
    assert summary["ready_for_live_explore"] is False
    assert summary["llm_live_preflight"]["reason"] == "llm_invalid_json"
    assert summary["capabilities"]["generate_adapters"]["local_ready"] is True
    assert summary["capabilities"]["generate_adapters"]["live_blockers"] == ["llm_live"]
    assert MALFORMED_PROBE not in json.dumps(payload)
    invoke.assert_awaited_once()


def test_strict_cli_doctor_blocks_malformed_probe(malformed_live_probe):
    result = CliRunner().invoke(cli, ["doctor", "--llm-live", "--require-capability", "generate_adapters", "--json"])
    assert result.exit_code == 1
    _assert_strict_probe_blocked(json.loads(result.stdout), malformed_live_probe)


@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http"])
async def test_strict_doctor_sdk_and_http_block_malformed_probe(malformed_live_probe, entrypoint):
    sdk = ClanySite()
    if entrypoint == "sdk":
        payload = await sdk.doctor(llm_live=True, require_capability="generate_adapters")
    else:
        server = APIServer()
        server._sdk = sdk
        async with TestClient(TestServer(server._build_app())) as client:
            response = await client.get("/doctor?llm_live=true&require_capability=generate_adapters")
            assert response.status == 503
            payload = await response.json()
    assert payload["success"] is False
    _assert_strict_probe_blocked(payload, malformed_live_probe)
