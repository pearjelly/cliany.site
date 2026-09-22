# src/cliany_site/browser/cdp.py
import asyncio
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
    port = parsed.port or (443 if parsed.scheme in {"https", "wss"} else 9222)
    return host, port


class CDPConnection:
    def __init__(
        self,
        cdp_url: str | None = None,
        headless: bool | None = None,
        provider_name: str | None = None,
    ):
        cfg = get_config()
        self._headless: bool = headless if headless is not None else cfg.headless
        self._session: BrowserSession | None = None
        self._chrome_proc: subprocess.Popen | None = None
        self._chrome_auto_launched: bool = False

        # URL 优先级：显式 cdp_url > CLIANY_CDP_URL > provider factory > 空（走 Chrome 默认路径）
        if cdp_url:
            self._cdp_url: str = cdp_url
        elif cfg.cdp_url:
            self._cdp_url = cfg.cdp_url
        else:
            effective_provider = (provider_name or cfg.browser_provider or "").lower()
            if effective_provider and effective_provider != "chrome":
                from cliany_site.providers.factory import get_provider
                _provider = get_provider(effective_provider)
                self._cdp_url = _provider.get_cdp_url()
            else:
                self._cdp_url = ""

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

    def _connection_url(self, port: int | None = None) -> str:
        if not self._cdp_url:
            return f"http://localhost:{port or get_config().cdp_port}"
        url = self._cdp_url.strip()
        parsed = urlparse(url if "://" in url else f"http://{url}")
        # Legacy ws://host:port denotes an HTTP discovery endpoint, not a socket path.
        if parsed.scheme == "ws" and parsed.path in {"", "/"} and not parsed.query:
            parsed = parsed._replace(scheme="http")
        if parsed.scheme == "http" and parsed.port is None:
            parsed = parsed._replace(netloc=f"{parsed.netloc}:9222")
        return parsed.geturl()

    def _http_resource_url(self, resource: str, port: int | None = None) -> str:
        parsed = urlparse(self._connection_url(port))
        base_path = parsed.path.rstrip('/').removesuffix('/json/version')
        return parsed._replace(path=f"{base_path}/{resource}").geturl()

    async def _websocket_request(self, method: str) -> dict[str, Any]:
        async with (
            asyncio.timeout(get_config().cdp_timeout),
            aiohttp.ClientSession() as session,
            session.ws_connect(self._connection_url()) as socket,
        ):
            await socket.send_json({"id": 1, "method": method})
            while True:
                reply = await socket.receive_json()
                if not isinstance(reply, dict):
                    raise ValueError("Invalid CDP response")
                if reply.get("id") == 1:
                    result = reply.get("result")
                    if "error" in reply or not isinstance(result, dict):
                        raise ValueError("CDP request failed")
                    return result

    async def check_available(self, port: int | None = None) -> bool:
        host, resolved_port = self._resolve_host_port(port)

        endpoint = urlparse(self._connection_url(port))
        if (self.is_remote or endpoint.scheme in {"https", "ws", "wss"}
                or endpoint.query or endpoint.path not in {"", "/"}):
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
            if urlparse(self._connection_url(port)).scheme in {"ws", "wss"}:
                result = await self._websocket_request("Browser.getVersion")
                return isinstance(result.get("product"), str) and bool(result["product"])
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    self._http_resource_url("json/version", port),
                    timeout=aiohttp.ClientTimeout(total=get_config().cdp_timeout),
                ) as resp,
            ):
                if resp.status != 200:
                    return False
                discovery = await resp.json()
                if not isinstance(discovery, dict):
                    return False
                product = discovery.get("Browser")
                socket_url = discovery.get("webSocketDebuggerUrl")
                if (not isinstance(product, str) or not product.strip()
                        or not isinstance(socket_url, str) or any(char.isspace() for char in socket_url)):
                    return False
                endpoint = urlparse(socket_url)
                return (endpoint.scheme in {"ws", "wss"} and bool(endpoint.hostname)
                        and (endpoint.port is None or endpoint.port > 0))
        except (TimeoutError, aiohttp.ClientError, OSError, ValueError, TypeError):
            logger.debug("远程 CDP 探测失败 (%s:%d)", host, port)
            return False

    async def connect(self, port: int | None = None) -> BrowserSession:
        is_local = not self.is_remote
        profile = BrowserProfile(
            cdp_url=self._connection_url(port),
            is_local=is_local,
        )
        self._session = BrowserSession(browser_profile=profile)
        await self._session.start()
        return self._session

    async def get_pages(self, port: int | None = None) -> list[dict]:
        host, resolved_port = self._resolve_host_port(port)
        try:
            if urlparse(self._connection_url(port)).scheme in {"ws", "wss"}:
                targets = (await self._websocket_request("Target.getTargets")).get("targetInfos")
                if not isinstance(targets, list) or any(not isinstance(item, dict) for item in targets):
                    return []
                return [{**item, "id": item.get("targetId", "")} for item in targets]
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    self._http_resource_url("json/list", port),
                    timeout=aiohttp.ClientTimeout(total=get_config().cdp_timeout),
                ) as resp,
            ):
                if resp.status == 200:
                    result: list[dict[Any, Any]] = await resp.json()
                    return result
                return []
        except (TimeoutError, aiohttp.ClientError, OSError, ValueError, TypeError):
            logger.debug("获取标签页列表失败 (%s:%d)", host, resolved_port)
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


async def enable_network_capture(
    browser_session: BrowserSession,
    *,
    session_id: str | None = None,
) -> None:
    await browser_session.cdp_client.send.Network.enable(session_id=session_id)


async def enable_console_capture(
    browser_session: BrowserSession,
    *,
    session_id: str | None = None,
) -> None:
    await browser_session.cdp_client.send.Console.enable(session_id=session_id)


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
