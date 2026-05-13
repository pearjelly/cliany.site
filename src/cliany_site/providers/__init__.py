"""
providers — 浏览器 Provider 能力抽象

包含：
- CapabilitySnapshot / assess_axtree_capability（Task 1/2 产物）
- BrowserProvider ABC / ProviderError（Task 9 产物）
- get_provider() factory（Task 9 产物）
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CapabilitySnapshot:
    """浏览器 Provider 兼容能力快照。

    字段：
    - supports_axtree: provider 是否支持 Accessibility 域（AXTree 捕获前提）。
      browser-use DomService.get_serialized_dom_tree() 依赖 Accessibility.getFullAXTree，
      缺失此域则无法生成 selector_map / element_tree。
    - supports_explore: provider 是否满足 explore 主链路最低要求。
      当前定义：必须 supports_axtree == True，否则此字段为 False。

    Task 2 将在此基础上扩展 supports_login / supports_vision / supports_recording 等字段。
    """

    supports_axtree: bool
    supports_explore: bool


def assess_axtree_capability(available_domains: list[str]) -> CapabilitySnapshot:
    """根据 CDP 可用域列表评估 provider 对 AXTree 的支持能力。

    规则：
    - Accessibility 域存在 → supports_axtree = True
    - Accessibility 域缺失 → supports_axtree = False，supports_explore = False
      （explore 主链路依赖 AXTree，不得宣称 fully supported）

    Args:
        available_domains: Provider 暴露的 CDP 域名列表，例如
            Chrome: ["Target", "Page", "Runtime", "DOM", "Network", "Accessibility", ...]
            Obscura: ["Target", "Page", "Runtime", "DOM", "Network", "LP", ...]

    Returns:
        CapabilitySnapshot with supports_axtree and supports_explore.
    """
    supports_axtree = "Accessibility" in available_domains
    supports_explore = supports_axtree
    return CapabilitySnapshot(
        supports_axtree=supports_axtree,
        supports_explore=supports_explore,
    )


from cliany_site.providers.base import BrowserProvider, ProviderError  # noqa: E402
from cliany_site.providers.factory import get_provider  # noqa: E402

__all__ = [
    "CapabilitySnapshot",
    "assess_axtree_capability",
    "BrowserProvider",
    "ProviderError",
    "get_provider",
]
