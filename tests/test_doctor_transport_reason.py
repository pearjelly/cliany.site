import json
import socket
import ssl
from unittest.mock import AsyncMock

import pytest

from cliany_site.commands.doctor import (
    _enrich_checks,
    _human_action_for_check,
    _llm_live_preflight_summary,
    _run_llm_live_check,
    _transport_failure_details,
)
from cliany_site.envelope import ErrorCode
from cliany_site.errors import LlmUnavailableError


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("cause,reason", [
    (ssl.SSLCertVerificationError("private-marker"), "tls_certificate_verify_failed"),
    (ssl.SSLEOFError("private-marker"), "tls_connection_closed"),
    (socket.gaierror("private-marker"), "dns_resolution_failed"),
    (ConnectionRefusedError("private-marker"), "connection_refused"),
    (TimeoutError("private-marker"), "connection_timeout"),
])
async def test_live_check_exposes_only_safe_transport_category(monkeypatch, cause, reason, wrapped):
    middle = RuntimeError("private-marker")
    middle.__cause__ = cause
    failure = LlmUnavailableError("LLM upstream unavailable after retries")
    failure.__cause__ = middle
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda: object())
    monkeypatch.setattr(
        "cliany_site.explorer.engine._invoke_llm_with_retry", AsyncMock(side_effect=failure if wrapped else cause),
    )
    result = await _run_llm_live_check(True, "openai")
    assert result["status"] == "warning"
    assert result["details"]["transport_reason"] == reason
    assert "private-marker" not in json.dumps(result)
    assert _llm_live_preflight_summary([result])["transport_reason"] == reason
    assert _human_action_for_check(result)
    summary = _enrich_checks([result])
    assert summary["should_fix"][0]["action"] == _human_action_for_check(result)
    assert summary["llm_live_preflight"]["action"] == _human_action_for_check(result)
    assert "private-marker" not in json.dumps(summary)
    if reason == "tls_certificate_verify_failed":
        assert "不要关闭证书验证" in _human_action_for_check(result)


def test_unknown_or_cyclic_exception_chain_is_not_guessed():
    error = RuntimeError("certificate error in arbitrary upstream text")
    error.__cause__ = error
    assert _transport_failure_details(error) == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_live_check_sanitizes_authentication_response(monkeypatch, status_code):
    class AuthenticationError(Exception):
        def __init__(self):
            super().__init__("private-marker: upstream response body")
            self.status_code = status_code

    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda: object())
    monkeypatch.setattr(
        "cliany_site.explorer.engine._invoke_llm_with_retry",
        AsyncMock(side_effect=AuthenticationError()),
    )

    result = await _run_llm_live_check(True, "anthropic")
    assert result["details"]["error_code"] == ErrorCode.E_LLM_AUTH_FAILED
    assert result["details"]["retryable"] is False
    assert result["details"]["status_code"] == status_code
    assert "private-marker" not in json.dumps(result)
    assert "密钥" in _enrich_checks([result])["llm_live_preflight"]["action"]
