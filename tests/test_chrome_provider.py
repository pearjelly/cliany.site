from __future__ import annotations

import pytest

from cliany_site.providers.chrome import ChromeProvider
from cliany_site.providers.factory import get_provider


class TestFactoryDefaultIsChrome:
    def test_no_env_returns_chrome_provider(self, monkeypatch):
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        provider = get_provider()
        assert isinstance(provider, ChromeProvider)

    def test_env_chrome_returns_chrome_provider(self, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "chrome")
        provider = get_provider()
        assert isinstance(provider, ChromeProvider)

    def test_explicit_chrome_returns_chrome_provider(self):
        provider = get_provider("chrome")
        assert isinstance(provider, ChromeProvider)


class TestGetCdpUrl:
    def test_local_path_uses_config_port(self, monkeypatch):
        monkeypatch.delenv("CLIANY_CDP_URL", raising=False)
        monkeypatch.delenv("CLIANY_CDP_PORT", raising=False)
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider()
        assert p.get_cdp_url() == "http://localhost:9222"

    def test_custom_port_from_env(self, monkeypatch):
        monkeypatch.setenv("CLIANY_CDP_PORT", "9999")
        monkeypatch.delenv("CLIANY_CDP_URL", raising=False)
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider()
        assert p.get_cdp_url() == "http://localhost:9999"

    def test_remote_cdp_url_returned_as_is(self, monkeypatch):
        monkeypatch.delenv("CLIANY_CDP_URL", raising=False)
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider(cdp_url="ws://remote-host:9222")
        assert p.get_cdp_url() == "ws://remote-host:9222"

    def test_explicit_cdp_url_overrides_env(self, monkeypatch):
        monkeypatch.setenv("CLIANY_CDP_URL", "ws://env-host:8888")
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider(cdp_url="ws://explicit:9222")
        assert p.get_cdp_url() == "ws://explicit:9222"

    def test_env_cdp_url_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setenv("CLIANY_CDP_URL", "ws://env-host:8888")
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider()
        assert p.get_cdp_url() == "ws://env-host:8888"


class TestGetCapabilitySnapshot:
    def test_full_capabilities(self):
        snap = ChromeProvider().get_capability_snapshot()
        assert snap.provider == "chrome"
        assert snap.supports_axtree is True
        assert snap.supports_navigation is True
        assert snap.supports_screenshot is True
        assert snap.supports_cookies is True
        assert snap.supports_network_events is True
        assert snap.supports_console_events is True

    def test_provider_name_field(self):
        snap = ChromeProvider().get_capability_snapshot()
        assert snap.provider == "chrome"


class TestClose:
    def test_close_is_noop(self):
        p = ChromeProvider()
        p.close()


class TestHeadless:
    def test_default_headless_false(self, monkeypatch):
        monkeypatch.delenv("CLIANY_HEADLESS", raising=False)
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider()
        assert p._headless is False

    def test_explicit_headless_true(self):
        p = ChromeProvider(headless=True)
        assert p._headless is True

    def test_env_headless(self, monkeypatch):
        monkeypatch.setenv("CLIANY_HEADLESS", "true")
        from cliany_site.config import reset_config
        reset_config()
        p = ChromeProvider()
        assert p._headless is True
