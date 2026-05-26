from __future__ import annotations

import platform as _platform
import sys

from cliany_site.binary.cache import CacheError, CacheManager
from cliany_site.binary.platforms import UnsupportedPlatformError, normalize_platform
from cliany_site.config import get_config
from cliany_site.envelope import ErrorCode
from cliany_site.providers.base import BrowserProvider, ProviderError
from cliany_site.providers.capabilities import CapabilitySnapshot

MIN_VERSION = "0.1.0"


def _version_tuple(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


MIN_VERSION_TUPLE = _version_tuple(MIN_VERSION)


def _check_min_version(version: str) -> None:
    if _version_tuple(version) < MIN_VERSION_TUPLE:
        raise ProviderError(
            f"Obscura 版本 {version!r} 低于最小要求 {MIN_VERSION!r}",
            error_code=ErrorCode.E_PROVIDER_VERSION_TOO_OLD,
        )


def _check_platform() -> None:
    try:
        normalize_platform(sys.platform, _platform.machine())
    except UnsupportedPlatformError as exc:
        raise ProviderError(
            f"不支持的平台: {exc.target_key}",
            error_code=ErrorCode.E_UNSUPPORTED_PLATFORM,
        ) from exc


class ObscuraProvider(BrowserProvider):
    name = "obscura"

    def __init__(self, source: str = "external", cdp_url: str | None = None):
        self._source = source
        self._explicit_cdp_url = cdp_url
        self._version: str = ""

        _check_platform()

        if source == "external":
            pass
        elif source == "managed":
            self._init_managed()
        else:
            raise ProviderError(
                f"未知 source: {source!r}，支持 'external' 或 'managed'",
                error_code=ErrorCode.E_PROVIDER_NOT_FOUND,
            )

    def _init_managed(self) -> None:
        mgr = CacheManager()
        version = mgr._get_active_version()

        if version is None:
            versions = mgr.list_versions()
            if not versions:
                raise ProviderError(
                    "managed 模式：未找到已安装的 Obscura 版本",
                    error_code=ErrorCode.E_BINARY_NOT_FOUND,
                )
            version = versions[-1]

        try:
            mgr.get_binary_path(version)
        except CacheError as exc:
            raise ProviderError(
                f"managed 模式：Obscura 二进制未找到（版本 {version}）",
                error_code=ErrorCode.E_BINARY_NOT_FOUND,
            ) from exc

        _check_min_version(version)
        self._version = version

    def get_cdp_url(self) -> str:
        if self._explicit_cdp_url:
            return self._explicit_cdp_url
        return f"http://localhost:{get_config().obscura_port}"

    def get_capability_snapshot(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            provider="obscura",
            version=self._version,
            supports_axtree=False,
            supports_navigation=False,
            supports_screenshot=True,
            supports_cookies=False,
            supports_network_events=True,
            supports_console_events=True,
        )

    def close(self) -> None:
        pass
