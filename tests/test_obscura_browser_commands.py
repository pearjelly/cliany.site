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


def _make_no_nav_snap():
    return CapabilitySnapshot(
        provider="custom",
        version="0.1.0",
        supports_axtree=False,
        supports_navigation=False,
        supports_screenshot=True,
        supports_cookies=True,
        supports_network_events=False,
        supports_console_events=False,
    )


def _make_no_screenshot_snap():
    return CapabilitySnapshot(
        provider="custom",
        version="0.1.0",
        supports_axtree=False,
        supports_navigation=True,
        supports_screenshot=False,
        supports_cookies=True,
        supports_network_events=False,
        supports_console_events=False,
    )


def _make_mock_provider(snap):
    provider = MagicMock()
    provider.get_capability_snapshot.return_value = snap
    return provider


def _make_unavailable_cdp():
    mock_cdp = MagicMock()

    async def _check_unavailable():
        return False

    mock_cdp.check_available = _check_unavailable
    return mock_cdp


class TestCapabilityGatePure:
    def test_navigate_gate_allowed_for_obscura(self):
        gate = feature_gate("browser.navigate", _make_obscura_snap())
        assert gate.allowed is True

    def test_screenshot_gate_allowed_for_obscura(self):
        gate = feature_gate("browser.screenshot", _make_obscura_snap())
        assert gate.allowed is True

    def test_navigate_gate_blocked_no_navigation(self):
        gate = feature_gate("browser.navigate", _make_no_nav_snap())
        assert gate.allowed is False
        assert "supports_navigation" in gate.reason

    def test_screenshot_gate_blocked_no_screenshot(self):
        gate = feature_gate("browser.screenshot", _make_no_screenshot_snap())
        assert gate.allowed is False
        assert "supports_screenshot" in gate.reason


class TestNavigateCommandGate:
    def test_navigate_passes_gate_under_obscura(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_obscura_snap())
        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider), \
             patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "navigate", "https://example.com"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"

    def test_navigate_blocked_when_no_navigation_support(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_nav_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "navigate", "https://example.com"], catch_exceptions=False)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_MISSING_CAPABILITY"

    def test_navigate_gate_reason_in_hint(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_nav_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "navigate", "https://example.com"], catch_exceptions=False)

        data = json.loads(result.output)
        assert "supports_navigation" in data["error"]["hint"]

    def test_navigate_chrome_bypasses_gate(self, tmp_home, monkeypatch):
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "navigate", "https://example.com"], catch_exceptions=False)
            mock_factory.assert_not_called()

        data = json.loads(result.output)
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"

    def test_navigate_explicit_chrome_bypasses_gate(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "chrome")
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "navigate", "https://example.com"], catch_exceptions=False)
            mock_factory.assert_not_called()

        data = json.loads(result.output)
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"


class TestScreenshotCommandGate:
    def test_screenshot_passes_gate_under_obscura(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_obscura_snap())
        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider), \
             patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "screenshot"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"

    def test_screenshot_blocked_when_no_screenshot_support(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_screenshot_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "screenshot"], catch_exceptions=False)

        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_MISSING_CAPABILITY"

    def test_screenshot_chrome_bypasses_gate(self, tmp_home, monkeypatch):
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "screenshot"], catch_exceptions=False)
            mock_factory.assert_not_called()

        data = json.loads(result.output)
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"

    def test_screenshot_gate_error_envelope_structure(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_screenshot_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "screenshot"], catch_exceptions=False)

        data = json.loads(result.output)
        assert "ok" in data
        assert "version" in data
        assert "command" in data
        assert "error" in data
        assert "meta" in data
        assert data["command"] == "browser screenshot"
        assert data["error"]["code"] == "E_MISSING_CAPABILITY"
        assert data["error"]["hint"] is not None


class TestFindClickTypeUnderObscura:
    def test_find_under_obscura_reaches_cdp_not_gated(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "find", "--value", "button"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"

    def test_click_under_obscura_reaches_cdp_not_gated(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "click", "--text", "submit"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"

    def test_type_under_obscura_reaches_cdp_not_gated(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "type", "--text", "search", "--value", "hello"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_CDP_UNAVAILABLE"
        assert data["error"]["code"] != "E_MISSING_CAPABILITY"


class TestNavigateSuccessUnderObscura:
    def test_navigate_succeeds_with_mocked_cdp(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_obscura_snap())

        mock_session = MagicMock()

        async def _navigate_to(url):
            pass

        mock_session.navigate_to = _navigate_to

        mock_cdp = MagicMock()

        async def _check_available():
            return True

        async def _connect():
            return mock_session

        async def _disconnect():
            pass

        mock_cdp.check_available = _check_available
        mock_cdp.connect = _connect
        mock_cdp.disconnect = _disconnect

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider), \
             patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "browser", "navigate", "https://example.com"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["url"] == "https://example.com"
        assert data["data"]["status"] == "navigated"
