"""Distinguish Chromium page transport errors from CDP connection failures."""

from collections.abc import Iterator
from contextlib import contextmanager

from cliany_site.errors import ClanySiteError

_PREFIX = "Navigation failed: net::"
_TRANSPORT_ERRORS = frozenset({
    "ERR_ADDRESS_UNREACHABLE",
    "ERR_CONNECTION_CLOSED",
    "ERR_CONNECTION_REFUSED",
    "ERR_CONNECTION_RESET",
    "ERR_CONNECTION_TIMED_OUT",
    "ERR_EMPTY_RESPONSE",
    "ERR_INTERNET_DISCONNECTED",
    "ERR_NAME_NOT_RESOLVED",
    "ERR_TIMED_OUT",
})


class NavigationTransportError(ClanySiteError):
    reason = "navigation_transport_failed"
    hint = "请先在普通浏览器确认目标站点在当前网络可访问，再手动重试；不要绕过站点验证。"

    def __init__(self, browser_error: str) -> None:
        super().__init__("目标页面导航连接失败")
        self.details = {"phase": "navigation", "reason": self.reason, "browser_error": browser_error}


@contextmanager
def classify_navigation_transport() -> Iterator[None]:
    """Wrap only the navigation call, not discovery, connection or cleanup."""
    try:
        yield
    except RuntimeError as exc:
        # browser-use raises this exact prefix for Page.navigate's errorText.
        message = str(exc)
        if message.startswith(_PREFIX) and (code := message[len(_PREFIX):]) in _TRANSPORT_ERRORS:
            raise NavigationTransportError(code) from exc
        raise
