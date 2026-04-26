# src/cliany_site/browser/cdp.py
import logging
import subprocess
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import aiohttp
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession

from cliany_site.browser.launcher import (
    ChromeNotFoundError,
    ensure_chrome,
)
from cliany_site.config import get_config

logger = logging.getLogger(__name__)


def _parse_cdp_url(cdp_url: str) -> tuple[str, int]:
    url = cdp_url.strip()
    if "://" not in url:
        url = f"http://{url}"
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 9222
    return host, port


class CDPConnection:
    def __init__(
        self,
        cdp_url: str | None = None,
        headless: bool | None = None,
    ):
        cfg = get_config()
        self._cdp_url: str = cdp_url or cfg.cdp_url
        self._headless: bool = headless if headless is not None else cfg.headless
        self._session: BrowserSession | None = None
        self._chrome_proc: subprocess.Popen | None = None
        self._chrome_auto_launched: bool = False

    @property
    def is_remote(self) -> bool:
        if not self._cdp_url:
            return False
        host, _ = _parse_cdp_url(self._cdp_url)
        return host not in ("localhost", "127.0.0.1", "::1")

    def _resolve_host_port(self, port: int | None = None) -> tuple[str, int]:
        if self._cdp_url:
            return _parse_cdp_url(self._cdp_url)
        return "localhost", port or get_config().cdp_port

    async def check_available(self, port: int | None = None) -> bool:
        host, resolved_port = self._resolve_host_port(port)

        if self.is_remote:
            return await self._probe_remote(host, resolved_port)

        try:
            ws_url, proc = ensure_chrome(resolved_port, headless=self._headless)
            if proc is not None:
                self._chrome_proc = proc
                self._chrome_auto_launched = True
            return True
        except ChromeNotFoundError:
            return False
        except (RuntimeError, TimeoutError, OSError) as exc:
            logger.debug("CDP 可用性检查失败 (port=%d): %s", resolved_port, exc)
            return False

    async def _probe_remote(self, host: str, port: int) -> bool:
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"http://{host}:{port}/json/version",
                    timeout=aiohttp.ClientTimeout(total=get_config().cdp_timeout),
                ) as resp,
            ):
                return resp.status == 200
        except (TimeoutError, aiohttp.ClientError, OSError, ValueError) as exc:
            logger.debug("远程 CDP 探测失败 (%s:%d): %s", host, port, exc)
            return False

    async def connect(self, port: int | None = None) -> BrowserSession:
        host, resolved_port = self._resolve_host_port(port)
        is_local = not self.is_remote
        profile = BrowserProfile(
            cdp_url=f"http://{host}:{resolved_port}",
            is_local=is_local,
        )
        self._session = BrowserSession(browser_profile=profile)
        await self._session.start()
        return self._session

    async def get_pages(self, port: int | None = None) -> list[dict]:
        host, resolved_port = self._resolve_host_port(port)
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"http://{host}:{resolved_port}/json/list",
                    timeout=aiohttp.ClientTimeout(total=get_config().cdp_timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    result: list[dict[Any, Any]] = await resp.json()
                    return result
                return []
        except (TimeoutError, aiohttp.ClientError, OSError, ValueError) as exc:
            logger.debug("获取标签页列表失败 (%s:%d): %s", host, resolved_port, exc)
            return []

    async def disconnect(self):
        if self._session:
            try:
                await self._session.stop()
            except (OSError, RuntimeError) as exc:
                logger.debug("断开 CDP 会话时出错: %s", exc)
            self._session = None
        if self._chrome_proc:
            try:
                self._chrome_proc.terminate()
                self._chrome_proc.wait(timeout=5)
            except (OSError, subprocess.SubprocessError) as exc:
                logger.debug("终止 Chrome 进程时出错: %s", exc)
            self._chrome_proc = None


    @asynccontextmanager
    async def with_scope(self, name: str | None = None):
        from cliany_site.browser.session_scope import acquire_scope, release_scope

        scope = acquire_scope(
            name=name,
            scopes_path=get_config().sessions_dir / "scopes.json",
        )
        try:
            yield scope
        finally:
            release_scope(scope)


def cdp_from_context(ctx: Any) -> CDPConnection:
    obj: dict = {}
    if hasattr(ctx, "find_root"):
        root = ctx.find_root()
        obj = root.obj if isinstance(root.obj, dict) else {}
    elif isinstance(ctx, dict):
        obj = ctx
    return CDPConnection(
        cdp_url=obj.get("cdp_url"),
        headless=obj.get("headless"),
    )
