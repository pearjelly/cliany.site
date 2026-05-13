from __future__ import annotations

from cliany_site.config import get_config
from cliany_site.providers.base import BrowserProvider
from cliany_site.providers.capabilities import CapabilitySnapshot


class ChromeProvider(BrowserProvider):
    name = "chrome"

    def __init__(self, cdp_url: str | None = None, headless: bool | None = None):
        cfg = get_config()
        self._cdp_url: str = cdp_url if cdp_url is not None else cfg.cdp_url
        self._headless: bool = headless if headless is not None else cfg.headless

    def get_cdp_url(self) -> str:
        if self._cdp_url:
            return self._cdp_url
        return f"http://localhost:{get_config().cdp_port}"

    def get_capability_snapshot(self) -> CapabilitySnapshot:
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

    def close(self) -> None:
        pass
