"""沙箱模式 — 限制动作执行的安全边界

--sandbox 模式下：
  - navigate 仅允许同域跳转
  - 禁止文件下载触发
  - 禁止 JavaScript eval/exec 类操作
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from cliany_site.errors import ClanySiteError

logger = logging.getLogger(__name__)


class SandboxViolation(ClanySiteError):
    """沙箱策略违规"""


@dataclass(frozen=True)
class SandboxPolicy:
    enabled: bool = False
    allowed_domains: frozenset[str] = field(default_factory=frozenset)
    allow_downloads: bool = False
    allow_new_tabs: bool = True
    blocked_url_patterns: tuple[str, ...] = (
        "javascript:",
        "data:text/html",
        "file://",
    )

    @staticmethod
    def from_domain(domain: str) -> SandboxPolicy:
        return SandboxPolicy(
            enabled=True,
            allowed_domains=frozenset({domain, f"www.{domain}"}),
        )

    @staticmethod
    def permissive() -> SandboxPolicy:
        return SandboxPolicy(enabled=False)


def validate_navigation(url: str, policy: SandboxPolicy) -> None:
    """检查 URL 是否符合沙箱策略

    Raises:
        SandboxViolation: URL 违反沙箱策略
    """
    if not policy.enabled:
        return

    for pattern in policy.blocked_url_patterns:
        if url.lower().startswith(pattern):
            raise SandboxViolation(f"沙箱禁止访问: {pattern} 协议 (url={url})")

    parsed = urlparse(url)
    if not parsed.hostname:
        return

    hostname = parsed.hostname.lower()
    if not _domain_matches(hostname, policy.allowed_domains):
        raise SandboxViolation(f"沙箱禁止跨域导航: {hostname} 不在允许列表 {sorted(policy.allowed_domains)} 中")


def validate_action(action: dict[str, Any], policy: SandboxPolicy) -> None:
    """检查单个动作是否符合沙箱策略

    Raises:
        SandboxViolation: 动作违反沙箱策略
    """
    if not policy.enabled:
        return

    action_type = str(action.get("type") or action.get("action") or "").lower()

    if action_type == "navigate":
        url = str(action.get("url", ""))
        if url:
            validate_navigation(url, policy)

    if action_type == "evaluate" or action_type == "execute_js":
        raise SandboxViolation(f"沙箱禁止执行 JavaScript: action={action_type}")

    if action_type == "download" and not policy.allow_downloads:
        raise SandboxViolation("沙箱禁止文件下载")


def validate_action_steps(
    steps: list[dict[str, Any]],
    policy: SandboxPolicy,
) -> list[dict[str, str]]:
    """批量校验动作步骤，返回违规列表（空列表 = 全部通过）"""
    violations: list[dict[str, str]] = []
    for i, step in enumerate(steps):
        try:
            validate_action(step, policy)
        except SandboxViolation as exc:
            action_type = str(step.get("type") or step.get("action") or "")
            violations.append({"index": str(i), "action": action_type, "error": str(exc)})
    return violations


def _domain_matches(hostname: str, allowed: frozenset[str]) -> bool:
    """检查 hostname 是否匹配 allowed 域名（支持子域名匹配）"""
    if hostname in allowed:
        return True
    return any(hostname.endswith(f".{domain}") for domain in allowed)
