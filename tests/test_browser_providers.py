import os

import pytest

from cliany_site.envelope import ErrorCode
from cliany_site.providers.base import BrowserProvider, ProviderError
from cliany_site.providers.factory import _ChromeProviderStub, _ObscuraProviderStub, get_provider


class TestDefaultProvider:
    def test_default_provider_is_chrome(self, monkeypatch):
        monkeypatch.delenv("CLIANY_BROWSER_PROVIDER", raising=False)
        provider = get_provider()
        assert isinstance(provider, _ChromeProviderStub)

    def test_provider_env_var_chrome(self, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "chrome")
        provider = get_provider()
        assert isinstance(provider, _ChromeProviderStub)

    def test_provider_env_var_obscura(self, monkeypatch):
        monkeypatch.setenv("CLIANY_BROWSER_PROVIDER", "obscura")
        provider = get_provider()
        assert isinstance(provider, _ObscuraProviderStub)

    def test_provider_unknown_raises(self):
        with pytest.raises(ProviderError) as exc_info:
            get_provider("foobar")
        assert exc_info.value.error_code == ErrorCode.E_PROVIDER_NOT_FOUND


class TestProviderCapabilities:
    def test_chrome_has_axtree(self):
        provider = get_provider("chrome")
        assert provider.get_capability_snapshot().supports_axtree is True

    def test_obscura_lacks_axtree(self):
        provider = get_provider("obscura")
        assert provider.get_capability_snapshot().supports_axtree is False


class TestProviderInterface:
    def test_provider_has_close(self):
        provider = get_provider()
        assert callable(provider.close)

    def test_provider_has_cdp_url(self):
        provider = get_provider()
        url = provider.get_cdp_url()
        assert isinstance(url, str)
        assert len(url) > 0
