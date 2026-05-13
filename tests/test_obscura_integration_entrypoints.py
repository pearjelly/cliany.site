import json
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.providers.base import ProviderError


def _make_mock_cdp():
    class MockCDP:
        def __init__(self, cdp_url=None, headless=None, provider_name=None):
            self._cdp_url = cdp_url or ""
            self._headless = headless or False

        async def check_available(self):
            return True

    return MockCDP


def _invoke_doctor(monkeypatch, extra_env=None):
    monkeypatch.setattr("cliany_site.browser.cdp.CDPConnection", _make_mock_cdp())
    monkeypatch.setenv("CLIANY_ANTHROPIC_API_KEY", "test-key")
    if extra_env:
        for k, v in extra_env.items():
            monkeypatch.setenv(k, v)
    runner = CliRunner()
    return runner.invoke(cli, ["--json", "doctor"], catch_exceptions=False)


class TestDoctorProviderField:
    def test_provider_check_present_in_checks(self, tmp_home, no_llm, monkeypatch):
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        checks = data["data"]["checks"]
        names = [c["name"] for c in checks]
        assert "provider" in names

    def test_provider_check_has_required_structure(self, tmp_home, no_llm, monkeypatch):
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        checks = data["data"]["checks"]
        provider_check = next(c for c in checks if c["name"] == "provider")
        assert "name" in provider_check
        assert "status" in provider_check
        assert "duration_ms" in provider_check
        assert "details" in provider_check
        assert provider_check["status"] in ("ok", "warning", "fail")

    def test_provider_check_details_has_provider_name(self, tmp_home, no_llm, monkeypatch):
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        checks = data["data"]["checks"]
        provider_check = next(c for c in checks if c["name"] == "provider")
        assert "provider_name" in provider_check["details"]
        assert provider_check["details"]["provider_name"] == "chrome"

    def test_provider_check_details_has_capabilities(self, tmp_home, no_llm, monkeypatch):
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        checks = data["data"]["checks"]
        provider_check = next(c for c in checks if c["name"] == "provider")
        caps = provider_check["details"]["provider_capabilities"]
        assert caps is not None
        assert "supports_axtree" in caps
        assert "supports_navigation" in caps
        assert "provider" in caps

    def test_doctor_envelope_structure_unchanged(self, tmp_home, no_llm, monkeypatch):
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "ok" in data
        assert "version" in data
        assert "command" in data
        assert "data" in data
        assert "error" in data
        assert "meta" in data
        assert data["command"] == "doctor"
        assert data["ok"] is True
        assert "checks" in data["data"]


class TestCdpUrlBypassesProvider:
    def test_cdp_url_bypasses_provider_in_cdpconnection(self, monkeypatch):
        from cliany_site.browser.cdp import CDPConnection
        from cliany_site.config import reset_config

        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        reset_config()

        with patch("cliany_site.providers.obscura._check_platform"):
            cdp = CDPConnection(cdp_url="http://explicit:9333", provider_name="obscura")
            assert cdp._cdp_url == "http://explicit:9333"

    def test_cdp_url_used_directly_without_factory(self, monkeypatch):
        from cliany_site.browser.cdp import CDPConnection
        from cliany_site.config import reset_config

        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "chrome")
        reset_config()

        with patch("cliany_site.providers.factory.get_provider") as mock_factory:
            cdp = CDPConnection(cdp_url="http://my-remote:9222")
            assert cdp._cdp_url == "http://my-remote:9222"
            mock_factory.assert_not_called()


class TestUnknownProviderStructuredFailure:
    def test_unknown_provider_gives_warning_in_doctor(self, tmp_home, no_llm, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "unknown-provider-xyz")
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        checks = data["data"]["checks"]
        provider_check = next(c for c in checks if c["name"] == "provider")
        assert provider_check["status"] == "warning"
        assert provider_check["details"]["provider_capabilities"] is None
        assert "error" in provider_check["details"]

    def test_unknown_provider_does_not_fail_overall_doctor(self, tmp_home, no_llm, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "unknown-provider-xyz")
        result = _invoke_doctor(monkeypatch)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True

    def test_unknown_provider_cdpconnection_raises_provider_error(self, monkeypatch):
        from cliany_site.browser.cdp import CDPConnection
        from cliany_site.config import reset_config

        monkeypatch.delenv("CLIANY_CDP_URL", raising=False)
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        reset_config()

        with pytest.raises(ProviderError):
            CDPConnection(provider_name="nonexistent-provider")
