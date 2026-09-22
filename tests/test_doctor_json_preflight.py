import json

import httpx
import langchain_openai
import pytest

from cliany_site.commands.doctor import _run_llm_live_check


@pytest.mark.asyncio
async def test_openai_preflight_satisfies_json_mode(tmp_home, clean_env, monkeypatch):
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
                "role": "assistant", "content": '{"status":"ok"}',
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
            **kwargs, http_async_client=client, max_retries=0,
        ))
        result = await _run_llm_live_check(True, "openai")

    assert len(requests) == 1
    assert result["status"] == "ok"
    assert result["details"]["phase"] == "llm_preflight"
