import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cliany_site.providers.capabilities import CapabilitySnapshot, feature_gate


def _make_obscura_snap():
    return CapabilitySnapshot(
        provider="obscura",
        version="0.1.0",
        supports_axtree=False,
        supports_navigation=True,
        supports_screenshot=True,
        supports_cookies=True,
        supports_network_events=True,
        supports_console_events=True,
    )


def _make_chrome_snap():
    return CapabilitySnapshot(
        provider="chrome",
        version="",
        supports_axtree=True,
        supports_navigation=True,
        supports_screenshot=True,
        supports_cookies=True,
        supports_network_events=True,
        supports_console_events=True,
    )


class TestFeatureGatePure:
    def test_explore_gate_denied_when_no_axtree(self):
        gate = feature_gate("explore", _make_obscura_snap())
        assert gate.allowed is False

    def test_explore_gate_allowed_when_axtree(self):
        gate = feature_gate("explore", _make_chrome_snap())
        assert gate.allowed is True

    def test_explore_gate_reason_mentions_axtree_when_denied(self):
        gate = feature_gate("explore", _make_obscura_snap())
        assert "supports_axtree" in gate.reason

    def test_navigate_gate_unaffected_by_axtree_false(self):
        snap = _make_obscura_snap()
        assert snap.supports_axtree is False
        gate = feature_gate("browser.navigate", snap)
        assert gate.allowed is True


class TestExploreCommandGate:
    def _make_mock_provider(self, snap):
        provider = MagicMock()
        provider.get_capability_snapshot.return_value = snap
        return provider

    def test_obscura_provider_returns_missing_capability(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        obscura_provider = self._make_mock_provider(_make_obscura_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=obscura_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "explore", "https://example.com", "搜索"], catch_exceptions=False)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_MISSING_CAPABILITY"

    def test_obscura_provider_does_not_return_success(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        obscura_provider = self._make_mock_provider(_make_obscura_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=obscura_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "explore", "https://example.com", "搜索"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is not True

    def test_chrome_provider_passes_gate_hits_cdp_check(self, tmp_home, monkeypatch):
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = MagicMock()
        mock_cdp.check_available = MagicMock(return_value=False)

        async def _check_available():
            return False

        mock_cdp.check_available = _check_available

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "explore", "https://example.com", "搜索"], catch_exceptions=False)
            mock_factory.assert_not_called()

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"

    def test_explicit_chrome_provider_not_gated(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "chrome")
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = MagicMock()

        async def _check_available():
            return False

        mock_cdp.check_available = _check_available

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "explore", "https://example.com", "搜索"], catch_exceptions=False)
            mock_factory.assert_not_called()

        data = json.loads(result.output)
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"

    def test_gate_error_envelope_structure(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        obscura_provider = self._make_mock_provider(_make_obscura_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=obscura_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "explore", "https://example.com", "搜索"], catch_exceptions=False)

        data = json.loads(result.output)
        assert "ok" in data
        assert "version" in data
        assert "command" in data
        assert "error" in data
        assert "meta" in data
        assert data["command"] == "explore"
        assert data["error"]["code"] == "E_MISSING_CAPABILITY"
        assert data["error"]["hint"] is not None
