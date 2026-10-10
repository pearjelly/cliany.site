import io
import json
import logging
from http import HTTPStatus

import httpx
import pytest

from cliany_site.errors import LlmUnavailableError
from cliany_site.explorer.engine import (
    _extract_status_code,
    _invoke_llm_with_retry,
    _llm_error_summary,
    _llm_failure_reason,
)
from cliany_site.progress import NdjsonProgressReporter


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
async def test_http_rejection_is_not_retried_despite_gateway_body(tmp_home, status):
    class Rejected(Exception):
        status_code = status

    class LLM:
        calls = 0

        async def ainvoke(self, _prompt):
            self.calls += 1
            raise Rejected("<html><title>private token: Bad Gateway</title></html>")

    model = LLM()
    stream = io.StringIO()
    with pytest.raises(LlmUnavailableError) as caught:
        await _invoke_llm_with_retry(
            model, "private prompt", max_attempts=3, base_delay=0,
            progress=NdjsonProgressReporter(file=stream),
        )
    assert model.calls == 1
    assert caught.value.status_code == status
    assert caught.value.retryable is False
    assert "private" not in str(caught.value)
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    failure = next(event for event in events if event["event"] == "explore_llm_attempt_error")
    assert failure["reason"] == ("authentication_failed" if status in {401, 403} else "request_rejected")
    assert failure["status_code"] == status
    assert failure["retryable"] is False
    assert "private" not in stream.getvalue()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,reason", [(429, "rate_limited"), (502, "upstream_http_error")])
async def test_retry_diagnostics_and_warning_exclude_provider_body(tmp_home, caplog, status, reason):
    class Unavailable(Exception):
        status_code = status

    class LLM:
        calls = 0

        async def ainvoke(self, _prompt):
            self.calls += 1
            if self.calls == 1:
                raise Unavailable("<html><title>private endpoint and token</title>Bad Gateway</html>")
            return "ok"

    model = LLM()
    stream = io.StringIO()
    with caplog.at_level(logging.WARNING, logger="cliany_site.explorer.engine"):
        result = await _invoke_llm_with_retry(
            model, "private prompt", max_attempts=2, base_delay=0,
            progress=NdjsonProgressReporter(file=stream),
        )
    assert result == "ok"
    assert model.calls == 2
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    failure = next(event for event in events if event["event"] == "explore_llm_attempt_error")
    assert {key: failure[key] for key in ("reason", "status_code", "retryable")} == {
        "reason": reason, "status_code": status, "retryable": True,
    }
    assert "private" not in stream.getvalue() + caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [TimeoutError("private"), httpx.ReadTimeout("private")])
async def test_typed_timeout_with_uninformative_message_recovers(tmp_home, failure):
    class LLM:
        calls = 0

        async def ainvoke(self, _prompt):
            self.calls += 1
            if self.calls == 1:
                raise failure
            return "ok"

    stream = io.StringIO()
    model = LLM()
    assert await _invoke_llm_with_retry(
        model, "private prompt", max_attempts=2, base_delay=0,
        progress=NdjsonProgressReporter(file=stream),
    ) == "ok"
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    failure_event = next(event for event in events if event["event"] == "explore_llm_attempt_error")
    assert failure_event["reason"] == "timeout"
    assert failure_event["status_code"] is None
    assert model.calls == 2
    assert "private" not in stream.getvalue()


def test_unstructured_gateway_summary_does_not_echo_private_details(tmp_home):
    message = _llm_error_summary(RuntimeError("Bad Gateway https://private.invalid?token=private"))
    assert "private" not in message
    assert "https://" not in message


@pytest.mark.parametrize("status", [True, "401", 99, 600])
def test_invalid_http_status_is_not_exposed(tmp_home, status):
    class Failure(Exception):
        status_code = status

    assert _extract_status_code(Failure("private")) is None


def test_cyclic_unrecognized_failure_is_not_guessed_from_private_text(tmp_home):
    failure = RuntimeError("private certificate details")
    failure.__cause__ = failure
    assert _llm_failure_reason(failure) == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [HTTPStatus.BAD_REQUEST, HTTPStatus.UNAUTHORIZED, HTTPStatus.TOO_MANY_REQUESTS])
async def test_sdk_http_status_enum_is_normalized_before_body_heuristics(tmp_home, status):
    from openai import APIStatusError

    response = httpx.Response(status, request=httpx.Request("POST", "https://fixture.invalid"))
    failure = APIStatusError("private Bad Gateway", response=response, body={})

    class LLM:
        calls = 0

        async def ainvoke(self, _prompt):
            self.calls += 1
            raise failure

    model = LLM()
    stream = io.StringIO()
    with pytest.raises(LlmUnavailableError) as caught:
        await _invoke_llm_with_retry(
            model, "prompt", max_attempts=2, base_delay=0,
            progress=NdjsonProgressReporter(file=stream),
        )
    assert model.calls == (2 if status == HTTPStatus.TOO_MANY_REQUESTS else 1)
    assert caught.value.status_code == int(status)
    assert type(caught.value.status_code) is int
    assert caught.value.retryable is (status == HTTPStatus.TOO_MANY_REQUESTS)
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    errors = [event for event in events if event["event"] == "explore_llm_attempt_error"]
    assert all(event["status_code"] == int(status) for event in errors)
    assert "private" not in stream.getvalue()


@pytest.mark.asyncio
async def test_legacy_attempt_reporter_needs_no_new_callback(tmp_home):
    class Reporter:
        def on_explore_llm_attempt_start(self, *_args):
            pass

        def on_explore_llm_attempt_done(self, *_args):
            pass

    class LLM:
        calls = 0

        async def ainvoke(self, _prompt):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("timed out")
            return "ok"

    assert await _invoke_llm_with_retry(
        LLM(), "prompt", max_attempts=2, base_delay=0, progress=Reporter(),
    ) == "ok"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 400])
async def test_real_openai_http_rejection_stops_after_one_request(tmp_home, clean_env, monkeypatch, status):
    import langchain_openai

    from cliany_site.explorer.engine import _get_llm

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, json={"error": {"message": "private Bad Gateway token"}})

    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("cliany_site.explorer.engine._load_dotenv", lambda: None)
    original = langchain_openai.ChatOpenAI
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as client:
        monkeypatch.setattr(langchain_openai, "ChatOpenAI", lambda **kwargs: original(
            **kwargs, http_async_client=client,
        ))
        with pytest.raises(LlmUnavailableError) as caught:
            await _invoke_llm_with_retry(_get_llm(), "private JSON prompt", max_attempts=3, base_delay=0)
    assert len(requests) == 1
    assert caught.value.retryable is False
    assert "private" not in str(caught.value)


@pytest.mark.parametrize("status", [401, 403, 400])
def test_explore_http_failure_has_safe_nonretryable_envelope(tmp_home, clean_env, monkeypatch, status):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from click.testing import CliRunner

    from cliany_site.cli import cli

    class Rejected(Exception):
        status_code = status

    class LLM:
        async def ainvoke(self, _prompt):
            raise Rejected("private Bad Gateway token")

    class Explorer:
        def __init__(self, **_kwargs):
            pass

        async def explore(self, *_args, **kwargs):
            return await _invoke_llm_with_retry(LLM(), "private prompt", progress=kwargs["progress"], base_delay=0)

    monkeypatch.setenv("CLIANY_LLM_PROVIDER", "openai")
    monkeypatch.setenv("CLIANY_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLIANY_OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setattr("cliany_site.explorer.engine._load_dotenv", lambda: None)
    monkeypatch.setattr("cliany_site.explorer.engine.WorkflowExplorer", Explorer)
    monkeypatch.setattr("cliany_site.browser.cdp.cdp_from_context", lambda _ctx: SimpleNamespace(
        check_available=AsyncMock(return_value=True),
    ))
    result = CliRunner().invoke(cli, ["explore", "https://example.com", "read page", "--json"])
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == ("E_LLM_AUTH_FAILED" if status in {401, 403} else "E_LLM_UNAVAILABLE")
    assert payload["error"]["details"] == {"retryable": False, "status_code": status, "phase": "llm_invoke"}
    assert "private" not in result.output + json.dumps(payload)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_doctor_wrapped_http_auth_failure_keeps_auth_code(tmp_home, clean_env, monkeypatch, status):
    from cliany_site.commands.doctor import _run_llm_live_check

    class Rejected(Exception):
        status_code = status

    class LLM:
        async def ainvoke(self, _prompt):
            raise Rejected("private Bad Gateway token")

    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda: LLM())
    result = await _run_llm_live_check(True, "openai")
    assert result["details"]["error_code"] == "E_LLM_AUTH_FAILED"
    assert result["details"]["retryable"] is False
    assert "private" not in json.dumps(result)
