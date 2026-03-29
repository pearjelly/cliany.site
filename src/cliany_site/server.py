# ---------------------------------------------------------------------------
# cliany-site HTTP API 服务
# ---------------------------------------------------------------------------
"""轻量 REST API 服务器，暴露 cliany-site SDK 功能为 HTTP 端点。

启动方式::

    cliany-site serve --port 8080
    cliany-site serve --host 0.0.0.0 --port 9000

端点::

    GET  /health          — 健康检查
    GET  /doctor          — 环境诊断
    GET  /adapters        — 列出已安装 adapter
    POST /explore         — 探索工作流
    POST /execute         — 执行 adapter 命令
    POST /login           — 捕获 Session
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cliany_site.sdk import ClanySite

logger = logging.getLogger(__name__)


class APIServer:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        cdp_url: str | None = None,
        headless: bool | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._cdp_url = cdp_url
        self._headless = headless
        self._sdk: ClanySite | None = None

    async def _get_sdk(self) -> ClanySite:
        if self._sdk is None:
            self._sdk = ClanySite(cdp_url=self._cdp_url, headless=self._headless)
        return self._sdk

    def _build_app(self) -> Any:
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/health", self._handle_health)
        app.router.add_get("/doctor", self._handle_doctor)
        app.router.add_get("/adapters", self._handle_list_adapters)
        app.router.add_post("/explore", self._handle_explore)
        app.router.add_post("/execute", self._handle_execute)
        app.router.add_post("/login", self._handle_login)
        app.on_cleanup.append(self._cleanup)
        return app

    async def _cleanup(self, _app: Any) -> None:
        if self._sdk is not None:
            await self._sdk.close()
            self._sdk = None

    @staticmethod
    def _json_response(data: dict[str, Any], status: int = 200) -> Any:
        from aiohttp import web

        return web.json_response(data, status=status)

    async def _handle_health(self, _request: Any) -> Any:
        return self._json_response({"status": "ok"})

    async def _handle_doctor(self, _request: Any) -> Any:
        sdk = await self._get_sdk()
        result = await sdk.doctor()
        status = 200 if result.get("success") else 503
        return self._json_response(result, status=status)

    async def _handle_list_adapters(self, request: Any) -> Any:
        detail = request.query.get("detail", "").lower() in ("1", "true", "yes")
        sdk = await self._get_sdk()
        result = await sdk.list_adapters(detail=detail)
        return self._json_response(result)

    async def _handle_explore(self, request: Any) -> Any:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return self._json_response(
                {"success": False, "data": None, "error": {"code": "BAD_REQUEST", "message": "无效的 JSON 请求体"}},
                status=400,
            )

        url = body.get("url")
        workflow = body.get("workflow") or body.get("workflow_description")
        if not url or not workflow:
            return self._json_response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": "BAD_REQUEST", "message": "缺少 url 或 workflow 字段"},
                },
                status=400,
            )

        force = bool(body.get("force", False))
        sdk = await self._get_sdk()
        result = await sdk.explore(url, workflow, force=force)
        status = 200 if result.get("success") else 500
        return self._json_response(result, status=status)

    async def _handle_execute(self, request: Any) -> Any:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return self._json_response(
                {"success": False, "data": None, "error": {"code": "BAD_REQUEST", "message": "无效的 JSON 请求体"}},
                status=400,
            )

        domain = body.get("domain")
        command = body.get("command")
        if not domain or not command:
            return self._json_response(
                {
                    "success": False,
                    "data": None,
                    "error": {"code": "BAD_REQUEST", "message": "缺少 domain 或 command 字段"},
                },
                status=400,
            )

        params = body.get("params")
        dry_run = bool(body.get("dry_run", False))
        sdk = await self._get_sdk()
        result = await sdk.execute(domain, command, params=params, dry_run=dry_run)
        status = 200 if result.get("success") else 500
        return self._json_response(result, status=status)

    async def _handle_login(self, request: Any) -> Any:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return self._json_response(
                {"success": False, "data": None, "error": {"code": "BAD_REQUEST", "message": "无效的 JSON 请求体"}},
                status=400,
            )

        url = body.get("url")
        if not url:
            return self._json_response(
                {"success": False, "data": None, "error": {"code": "BAD_REQUEST", "message": "缺少 url 字段"}},
                status=400,
            )

        sdk = await self._get_sdk()
        result = await sdk.login(url)
        status = 200 if result.get("success") else 500
        return self._json_response(result, status=status)

    def run(self) -> None:
        from aiohttp import web

        app = self._build_app()
        logger.info("启动 HTTP API 服务: %s:%d", self._host, self._port)
        web.run_app(app, host=self._host, port=self._port, print=lambda msg: logger.info(msg))
