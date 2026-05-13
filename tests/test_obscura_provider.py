from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cliany_site.binary.cache import CacheError
from cliany_site.binary.platforms import UnsupportedPlatformError
from cliany_site.envelope import ErrorCode
from cliany_site.providers.base import ProviderError
from cliany_site.providers.factory import get_provider
from cliany_site.providers.obscura import MIN_VERSION, ObscuraProvider, _check_min_version


def _make_cache_manager_mock(version="0.2.0", binary_path=Path("/fake/obscura")):
    mgr = MagicMock()
    mgr._get_active_version.return_value = version
    mgr.get_binary_path.return_value = binary_path
    return mgr


class TestExternalSourceInit:
    def test_external_init_default(self):
        p = ObscuraProvider(source="external")
        assert p._source == "external"
        assert p._version == ""

    def test_external_init_with_custom_cdp_url(self):
        p = ObscuraProvider(source="external", cdp_url="http://custom:9999")
        assert p._explicit_cdp_url == "http://custom:9999"


class TestManagedSourceInit:
    def test_managed_init_success(self):
        mock_mgr = _make_cache_manager_mock("0.2.0")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            p = ObscuraProvider(source="managed")
        assert p._version == "0.2.0"

    def test_managed_init_no_binary_raises(self):
        mock_mgr = MagicMock()
        mock_mgr._get_active_version.return_value = "0.2.0"
        mock_mgr.get_binary_path.side_effect = CacheError("not found", ErrorCode.E_BINARY_NOT_FOUND)
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            with pytest.raises(ProviderError) as exc_info:
                ObscuraProvider(source="managed")
        assert exc_info.value.error_code == ErrorCode.E_BINARY_NOT_FOUND

    def test_managed_init_no_versions_raises(self):
        mock_mgr = MagicMock()
        mock_mgr._get_active_version.return_value = None
        mock_mgr.list_versions.return_value = []
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            with pytest.raises(ProviderError) as exc_info:
                ObscuraProvider(source="managed")
        assert exc_info.value.error_code == ErrorCode.E_BINARY_NOT_FOUND

    def test_managed_init_fallback_to_list_versions(self):
        mock_mgr = MagicMock()
        mock_mgr._get_active_version.return_value = None
        mock_mgr.list_versions.return_value = ["0.1.0", "0.2.0"]
        mock_mgr.get_binary_path.return_value = Path("/fake/obscura")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            p = ObscuraProvider(source="managed")
        assert p._version == "0.2.0"


class TestGetCdpUrl:
    def test_external_default_uses_config_port(self, monkeypatch):
        monkeypatch.delenv("CLIANY_OBSCURA_PORT", raising=False)
        from cliany_site.config import reset_config
        reset_config()
        p = ObscuraProvider(source="external")
        assert p.get_cdp_url() == "http://localhost:9223"

    def test_external_with_explicit_cdp_url(self):
        p = ObscuraProvider(source="external", cdp_url="http://remote:9999")
        assert p.get_cdp_url() == "http://remote:9999"

    def test_managed_with_explicit_cdp_url(self):
        mock_mgr = _make_cache_manager_mock("0.2.0")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            p = ObscuraProvider(source="managed", cdp_url="http://mgd:8888")
        assert p.get_cdp_url() == "http://mgd:8888"


class TestGetCapabilitySnapshot:
    def test_supports_axtree_false(self):
        p = ObscuraProvider(source="external")
        snap = p.get_capability_snapshot()
        assert snap.supports_axtree is False

    def test_full_capabilities(self):
        p = ObscuraProvider(source="external")
        snap = p.get_capability_snapshot()
        assert snap.provider == "obscura"
        assert snap.supports_navigation is True
        assert snap.supports_screenshot is True
        assert snap.supports_cookies is True
        assert snap.supports_network_events is True
        assert snap.supports_console_events is True

    def test_managed_version_in_snapshot(self):
        mock_mgr = _make_cache_manager_mock("0.3.0")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            p = ObscuraProvider(source="managed")
        assert p.get_capability_snapshot().version == "0.3.0"

    def test_external_empty_version_in_snapshot(self):
        p = ObscuraProvider(source="external")
        assert p.get_capability_snapshot().version == ""


class TestVersionGate:
    def test_old_version_raises(self):
        mock_mgr = _make_cache_manager_mock("0.0.9")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            with pytest.raises(ProviderError) as exc_info:
                ObscuraProvider(source="managed")
        assert exc_info.value.error_code == ErrorCode.E_PROVIDER_VERSION_TOO_OLD

    def test_min_version_passes(self):
        mock_mgr = _make_cache_manager_mock("0.1.0")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            p = ObscuraProvider(source="managed")
        assert p._version == "0.1.0"

    def test_check_min_version_function_old(self):
        with pytest.raises(ProviderError) as exc_info:
            _check_min_version("0.0.1")
        assert exc_info.value.error_code == ErrorCode.E_PROVIDER_VERSION_TOO_OLD

    def test_check_min_version_function_ok(self):
        _check_min_version("0.1.0")
        _check_min_version("1.0.0")

    def test_version_newer_than_min_passes(self):
        mock_mgr = _make_cache_manager_mock("1.5.3")
        with patch("cliany_site.providers.obscura.CacheManager", return_value=mock_mgr):
            p = ObscuraProvider(source="managed")
        assert p._version == "1.5.3"


class TestUnsupportedPlatform:
    def test_unsupported_platform_raises(self):
        with patch("cliany_site.providers.obscura.normalize_platform") as mock_np:
            mock_np.side_effect = UnsupportedPlatformError("freebsd-x86_64")
            with pytest.raises(ProviderError) as exc_info:
                ObscuraProvider(source="external")
        assert exc_info.value.error_code == ErrorCode.E_UNSUPPORTED_PLATFORM


class TestClose:
    def test_close_is_noop(self):
        p = ObscuraProvider(source="external")
        p.close()


class TestFactoryIntegration:
    def test_unknown_provider_raises(self):
        with pytest.raises(ProviderError) as exc_info:
            get_provider("nonexistent_provider")
        assert exc_info.value.error_code == ErrorCode.E_PROVIDER_NOT_FOUND

    def test_obscura_from_factory(self):
        provider = get_provider("obscura")
        assert isinstance(provider, ObscuraProvider)
