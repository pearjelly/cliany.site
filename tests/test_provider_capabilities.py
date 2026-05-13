import pytest

from cliany_site.providers.capabilities import (
    CapabilitySnapshot,
    GateResult,
    feature_gate,
)


def _chrome_snap(**overrides) -> CapabilitySnapshot:
    defaults = dict(
        provider="chrome",
        version="120.0.0",
        supports_axtree=True,
        supports_navigation=True,
        supports_screenshot=True,
        supports_cookies=True,
        supports_network_events=True,
        supports_console_events=True,
    )
    defaults.update(overrides)
    return CapabilitySnapshot(**defaults)


def _obscura_snap(**overrides) -> CapabilitySnapshot:
    defaults = dict(
        provider="obscura",
        version="0.1.2",
        supports_axtree=False,
        supports_navigation=True,
        supports_screenshot=True,
        supports_cookies=True,
        supports_network_events=True,
        supports_console_events=True,
    )
    defaults.update(overrides)
    return CapabilitySnapshot(**defaults)


class TestGateResultType:
    def test_returns_gate_result_instance(self):
        result = feature_gate("explore", _chrome_snap())
        assert isinstance(result, GateResult)

    def test_allowed_is_bool(self):
        result = feature_gate("browser.navigate", _chrome_snap())
        assert isinstance(result.allowed, bool)

    def test_reason_is_str(self):
        result = feature_gate("explore", _obscura_snap())
        assert isinstance(result.reason, str)


class TestExploreGate:
    def test_explore_allowed_when_axtree_supported(self):
        assert feature_gate("explore", _chrome_snap()).allowed is True

    def test_explore_denied_when_axtree_missing(self):
        result = feature_gate("explore", _obscura_snap())
        assert result.allowed is False
        assert "supports_axtree" in result.reason

    def test_explore_allowed_reason_is_empty(self):
        result = feature_gate("explore", _chrome_snap())
        assert result.reason == ""


class TestLoginGate:
    def test_login_allowed_when_navigation_and_cookies(self):
        assert feature_gate("login", _chrome_snap()).allowed is True

    def test_login_denied_when_navigation_missing(self):
        result = feature_gate("login", _chrome_snap(supports_navigation=False))
        assert result.allowed is False
        assert "supports_navigation" in result.reason

    def test_login_denied_when_cookies_missing(self):
        result = feature_gate("login", _chrome_snap(supports_cookies=False))
        assert result.allowed is False
        assert "supports_cookies" in result.reason

    def test_login_denied_when_both_missing(self):
        result = feature_gate("login", _chrome_snap(supports_navigation=False, supports_cookies=False))
        assert result.allowed is False
        assert "supports_navigation" in result.reason
        assert "supports_cookies" in result.reason


class TestRecordingGate:
    def test_recording_allowed_when_network_events_supported(self):
        assert feature_gate("recording", _chrome_snap()).allowed is True

    def test_recording_denied_when_network_events_missing(self):
        result = feature_gate("recording", _chrome_snap(supports_network_events=False))
        assert result.allowed is False
        assert "supports_network_events" in result.reason


class TestBrowserNavigateGate:
    def test_navigate_allowed_when_navigation_supported(self):
        assert feature_gate("browser.navigate", _obscura_snap()).allowed is True

    def test_navigate_denied_when_navigation_missing(self):
        result = feature_gate("browser.navigate", _chrome_snap(supports_navigation=False))
        assert result.allowed is False
        assert "supports_navigation" in result.reason


class TestBrowserScreenshotGate:
    def test_screenshot_allowed(self):
        assert feature_gate("browser.screenshot", _chrome_snap()).allowed is True

    def test_screenshot_denied_when_missing(self):
        result = feature_gate("browser.screenshot", _chrome_snap(supports_screenshot=False))
        assert result.allowed is False
        assert "supports_screenshot" in result.reason


class TestUnknownFeature:
    def test_unknown_feature_denied(self):
        result = feature_gate("nonexistent.feature", _chrome_snap())
        assert result.allowed is False
        assert result.reason == "unknown_feature"

    def test_empty_string_feature_denied(self):
        result = feature_gate("", _chrome_snap())
        assert result.allowed is False

    def test_similar_name_denied(self):
        result = feature_gate("EXPLORE", _chrome_snap())
        assert result.allowed is False


class TestObscuraIntegration:
    def test_navigate_allowed_on_obscura(self):
        snap = _obscura_snap()
        assert feature_gate("browser.navigate", snap).allowed is True

    def test_explore_denied_on_obscura(self):
        snap = _obscura_snap()
        assert feature_gate("explore", snap).allowed is False

    def test_screenshot_allowed_on_obscura(self):
        snap = _obscura_snap()
        assert feature_gate("browser.screenshot", snap).allowed is True


class TestOptionalFields:
    def test_snapshot_platform_defaults_empty(self):
        snap = _chrome_snap()
        assert snap.platform == ""

    def test_snapshot_cdp_domains_defaults_none(self):
        snap = _chrome_snap()
        assert snap.cdp_domains is None

    def test_snapshot_accepts_platform_and_domains(self):
        snap = _chrome_snap(platform="darwin-arm64", cdp_domains=["Network", "Console"])
        assert snap.platform == "darwin-arm64"
        assert snap.cdp_domains == ["Network", "Console"]
