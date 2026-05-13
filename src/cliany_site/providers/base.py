from __future__ import annotations

from abc import ABC, abstractmethod

from cliany_site.envelope import ErrorCode
from cliany_site.errors import ClanySiteError
from cliany_site.providers.capabilities import CapabilitySnapshot


class ProviderError(ClanySiteError):
    def __init__(self, message: str, error_code: str = ErrorCode.E_PROVIDER_NOT_FOUND):
        self.error_code = error_code
        super().__init__(message)


class BrowserProvider(ABC):
    """浏览器 Provider 抽象基类。

    职责边界（三层）：
    1. 端点获取/启动 — get_cdp_url()
    2. 能力探测     — get_capability_snapshot()
    3. 生命周期     — close()

    不属于 Provider 层的职责：导航、AXTree 捕获、代码生成。
    """

    name: str  # 'chrome' | 'obscura' | 'external'

    @abstractmethod
    def get_cdp_url(self) -> str: ...

    @abstractmethod
    def get_capability_snapshot(self) -> CapabilitySnapshot: ...

    @abstractmethod
    def close(self) -> None: ...
