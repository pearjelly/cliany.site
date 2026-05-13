from __future__ import annotations

import os

from cliany_site.envelope import ErrorCode
from cliany_site.providers.base import BrowserProvider, ProviderError
from cliany_site.providers.chrome import ChromeProvider
from cliany_site.providers.obscura import ObscuraProvider

_ChromeProviderStub = ChromeProvider
_ObscuraProviderStub = ObscuraProvider

_REGISTRY: dict[str, type[BrowserProvider]] = {
    "chrome": ChromeProvider,
    "obscura": ObscuraProvider,
}


def get_provider(provider_name: str | None = None) -> BrowserProvider:
    if provider_name is None:
        provider_name = os.environ.get("CLIANY_BROWSER_PROVIDER") or "chrome"

    cls = _REGISTRY.get(provider_name)
    if cls is None:
        raise ProviderError(
            f"未知 browser provider: {provider_name!r}",
            error_code=ErrorCode.E_PROVIDER_NOT_FOUND,
        )
    return cls()
