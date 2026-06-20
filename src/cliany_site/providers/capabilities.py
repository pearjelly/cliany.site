from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CapabilitySnapshot:
    provider: str                  # 'chrome' | 'obscura' | 'external'
    version: str
    supports_axtree: bool          # Accessibility.getFullAXTree 是否可用
    supports_navigation: bool
    supports_screenshot: bool
    supports_cookies: bool
    supports_network_events: bool
    supports_console_events: bool
    platform: str = ""
    cdp_domains: list | None = field(default=None)


@dataclass
class GateResult:
    allowed: bool
    reason: str   # allowed=False 时描述缺失能力；allowed=True 时为空字符串


# 集中定义所有已知 feature 名，防止魔法值散落各命令文件
_KNOWN_FEATURES: frozenset[str] = frozenset(
    [
        "explore",
        "login",
        "recording",
        "browser.navigate",
        "browser.screenshot",
    ]
)


def feature_gate(feature: str, snapshot: CapabilitySnapshot) -> GateResult:
    if feature not in _KNOWN_FEATURES:
        return GateResult(allowed=False, reason="unknown_feature")

    if feature == "explore":
        if not snapshot.supports_axtree:
            return GateResult(allowed=False, reason="missing_capability:supports_axtree")
        return GateResult(allowed=True, reason="")

    if feature == "login":
        missing = []
        if not snapshot.supports_navigation:
            missing.append("supports_navigation")
        if not snapshot.supports_cookies:
            missing.append("supports_cookies")
        if missing:
            return GateResult(allowed=False, reason=f"missing_capability:{','.join(missing)}")
        return GateResult(allowed=True, reason="")

    if feature == "recording":
        if not snapshot.supports_network_events:
            return GateResult(allowed=False, reason="missing_capability:supports_network_events")
        return GateResult(allowed=True, reason="")

    if feature == "browser.navigate":
        if not snapshot.supports_navigation:
            return GateResult(allowed=False, reason="missing_capability:supports_navigation")
        return GateResult(allowed=True, reason="")

    if feature == "browser.screenshot":
        if not snapshot.supports_screenshot:
            return GateResult(allowed=False, reason="missing_capability:supports_screenshot")
        return GateResult(allowed=True, reason="")

    return GateResult(allowed=False, reason="unknown_feature")
