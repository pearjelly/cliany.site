import json
from pathlib import Path
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


def _make_no_cookies_snap():
    return CapabilitySnapshot(
        provider="custom",
        version="0.1.0",
        supports_axtree=False,
        supports_navigation=True,
        supports_screenshot=False,
        supports_cookies=False,
        supports_network_events=False,
        supports_console_events=False,
    )


def _make_no_network_snap():
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


class TestFeatureGatePureLoginRecording:
    def test_login_gate_allowed_for_obscura(self):
        gate = feature_gate("login", _make_obscura_snap())
        assert gate.allowed is True

    def test_login_gate_blocked_no_cookies(self):
        gate = feature_gate("login", _make_no_cookies_snap())
        assert gate.allowed is False
        assert "supports_cookies" in gate.reason

    def test_login_gate_blocked_no_navigation(self):
        snap = CapabilitySnapshot(
            provider="custom",
            version="0.1.0",
            supports_axtree=False,
            supports_navigation=False,
            supports_screenshot=False,
            supports_cookies=True,
            supports_network_events=False,
            supports_console_events=False,
        )
        gate = feature_gate("login", snap)
        assert gate.allowed is False
        assert "supports_navigation" in gate.reason

    def test_login_gate_reason_empty_when_allowed(self):
        gate = feature_gate("login", _make_obscura_snap())
        assert gate.reason == ""

    def test_recording_gate_allowed_for_obscura(self):
        gate = feature_gate("recording", _make_obscura_snap())
        assert gate.allowed is True

    def test_recording_gate_blocked_no_network_events(self):
        gate = feature_gate("recording", _make_no_network_snap())
        assert gate.allowed is False
        assert "supports_network_events" in gate.reason

    def test_obscura_axtree_false_blocks_explore_iframe_shadowdom(self):
        snap = _make_obscura_snap()
        assert snap.supports_axtree is False
        gate = feature_gate("explore", snap)
        assert gate.allowed is False
        assert "supports_axtree" in gate.reason


class TestLoginCommandGate:
    def test_login_obscura_passes_gate_reaches_cdp(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_obscura_snap())
        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider), \
             patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)

        data = json.loads(result.output)
        assert data.get("ok") is False or data.get("success") is False
        error_code = data.get("error", {}).get("code", "")
        assert error_code != "E_MISSING_CAPABILITY"
        assert "CDP" in error_code

    def test_login_blocked_when_no_cookies_support(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_cookies_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)

        assert result.exit_code == 1
        data = json.loads(result.output)
        error_code = data.get("error", {}).get("code", "")
        assert error_code == "E_MISSING_CAPABILITY"

    def test_login_gate_hint_contains_missing_capability_reason(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_cookies_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)

        data = json.loads(result.output)
        hint = data.get("error", {}).get("hint", "")
        assert "supports_cookies" in hint

    def test_login_chrome_bypasses_gate(self, tmp_home, monkeypatch):
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)
            mock_factory.assert_not_called()

        data = json.loads(result.output)
        error_code = data.get("error", {}).get("code", "")
        assert error_code != "E_MISSING_CAPABILITY"

    def test_login_explicit_chrome_bypasses_gate(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "chrome")
        from cliany_site.config import reset_config
        reset_config()

        mock_cdp = _make_unavailable_cdp()

        with patch("cliany_site.browser.cdp.CDPConnection", return_value=mock_cdp), \
             patch("cliany_site.providers.factory.get_provider") as mock_factory:
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)
            mock_factory.assert_not_called()

        data = json.loads(result.output)
        error_code = data.get("error", {}).get("code", "")
        assert error_code != "E_MISSING_CAPABILITY"

    def test_login_gate_error_envelope_structure(self, tmp_home, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "custom")
        from cliany_site.config import reset_config
        reset_config()

        mock_provider = _make_mock_provider(_make_no_cookies_snap())

        with patch("cliany_site.providers.factory.get_provider", return_value=mock_provider):
            from cliany_site.cli import cli
            runner = CliRunner()
            result = runner.invoke(cli, ["--json", "login", "https://example.com"], catch_exceptions=False)

        data = json.loads(result.output)
        assert "ok" in data
        assert "version" in data
        assert "command" in data
        assert "error" in data
        assert "meta" in data
        assert data["command"] == "login"
        assert data["error"]["code"] == "E_MISSING_CAPABILITY"
        assert data["error"]["hint"] is not None


class TestRecordingCapabilityGate:
    def test_recording_manager_start_recording_no_provider_gate(self, tmp_path):
        from cliany_site.explorer.recording import RecordingManager
        mgr = RecordingManager(base_dir=tmp_path / "recordings")
        manifest = mgr.start_recording(
            domain="example.com",
            url="https://example.com",
            workflow="test",
            session_id="sess-t18",
        )
        assert manifest.domain == "example.com"
        assert manifest.session_id == "sess-t18"

    def test_recording_manager_save_step_without_axtree(self, tmp_path):
        from cliany_site.explorer.models import StepRecord
        from cliany_site.explorer.recording import RecordingManager
        mgr = RecordingManager(base_dir=tmp_path / "recordings")
        manifest = mgr.start_recording("ex.com", "https://ex.com", "wf", "sess-t18-2")
        step = StepRecord(
            step_index=0,
            action_data={"type": "click"},
            llm_response_raw="resp",
            timestamp="2026-05-12T00:00:00Z",
        )
        mgr.save_step(manifest, step, screenshot_bytes=None, axtree_json=None)
        assert len(manifest.steps) == 1
        assert manifest.steps[0].axtree_snapshot_path is None

    def test_network_capture_start_stop_independent_of_provider(self):
        from cliany_site.browser.network_capture import NetworkCapture, start_network_capture, stop_network_capture
        cap = start_network_capture(None)
        assert isinstance(cap, NetworkCapture)
        result = stop_network_capture(cap)
        assert "requests" in result
        assert "count" in result

    def test_console_capture_start_stop_independent_of_provider(self):
        from cliany_site.browser.console_capture import ConsoleCapture, start_console_capture, stop_console_capture
        cap = start_console_capture(None)
        assert isinstance(cap, ConsoleCapture)
        result = stop_console_capture(cap)
        assert "entries" in result or "count" in result


class TestIframeShadowDomObscuraGate:
    def test_iframe_shadowdom_blocked_via_explore_gate_on_obscura(self):
        snap = _make_obscura_snap()
        gate = feature_gate("explore", snap)
        assert gate.allowed is False, "explore gate blocks Obscura; iframe/Shadow DOM requires AXTree"

    def test_chrome_explore_gate_allowed_supports_iframe_shadowdom(self):
        snap = CapabilitySnapshot(
            provider="chrome",
            version="",
            supports_axtree=True,
            supports_navigation=True,
            supports_screenshot=True,
            supports_cookies=True,
            supports_network_events=True,
            supports_console_events=True,
        )
        gate = feature_gate("explore", snap)
        assert gate.allowed is True
