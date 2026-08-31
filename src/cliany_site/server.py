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
    GET  /verify          — 严格静态验证一个 adapter
    POST /explore         — 探索工作流
    POST /execute         — 执行 adapter 命令
    POST /login           — 捕获 Session
"""

from __future__ import annotations

import importlib.metadata as metadata
import json
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from cliany_site.response import error_response
from cliany_site.sdk import ClanySite

if TYPE_CHECKING:
    from aiohttp.web import Application, Request, Response

logger = logging.getLogger(__name__)


_NOT_FOUND_ERROR_CODES = frozenset({"ADAPTER_NOT_FOUND", "COMMAND_NOT_FOUND"})
_BAD_REQUEST_ERROR_CODES = frozenset({"BAD_REQUEST", "E_INVALID_PARAM", "INVALID_URL"})
_UNPROCESSABLE_ERROR_CODES = frozenset(
    {"NO_COOKIES", "E_EMPTY_RESULT", "E_PARSE_FAILED", "E_VERIFY_STATIC", "E_VERIFY_SMOKE", "E_SANDBOX_VIOLATION"}
)
_UNAVAILABLE_ERROR_CODES = frozenset(
    {
        "CDP_UNAVAILABLE",
        "LLM_UNAVAILABLE",
        "E_CDP_UNAVAILABLE",
        "E_LLM_UNAVAILABLE",
        "E_MISSING_CAPABILITY",
    }
)


def _installed_version() -> str:
    try:
        return metadata.version("cliany-site")
    except metadata.PackageNotFoundError:
        return "unknown"


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

    def _build_app(self) -> Application:
        from aiohttp import web

        app = web.Application()
        app.router.add_get("/health", self._handle_health)
        app.router.add_get("/doctor", self._handle_doctor)
        app.router.add_get("/adapters", self._handle_list_adapters)
        app.router.add_get("/verify", self._handle_verify)
        app.router.add_post("/explore", self._handle_explore)
        app.router.add_post("/execute", self._handle_execute)
        app.router.add_post("/login", self._handle_login)
        app.on_cleanup.append(self._cleanup)
        return app

    async def _cleanup(self, _app: Application) -> None:
        if self._sdk is not None:
            await self._sdk.close()
            self._sdk = None

    @staticmethod
    def _json_response(data: dict[str, Any], status: int = 200) -> Response:
        from aiohttp import web

        return web.json_response(data, status=status)

    @staticmethod
    def _result_status(result: Mapping[str, Any]) -> int:
        """Map a standard SDK error envelope to an HTTP status code."""
        if result.get("success") is True:
            return 200

        error = result.get("error")
        code = error.get("code") if isinstance(error, Mapping) else None
        if code in _NOT_FOUND_ERROR_CODES:
            return 404
        if code in _BAD_REQUEST_ERROR_CODES:
            return 400
        if code in _UNPROCESSABLE_ERROR_CODES:
            return 422
        if code in _UNAVAILABLE_ERROR_CODES:
            return 503
        return 500

    @staticmethod
    def _bad_request(message: str) -> dict[str, Any]:
        return error_response("BAD_REQUEST", message)

    @staticmethod
    def _required_string(body: Mapping[str, Any], name: str) -> str | None:
        value = body.get(name)
        if not isinstance(value, str) or not value.strip():
            return None
        return value

    @staticmethod
    def _query_bool(request: Request, name: str) -> bool | None:
        values = request.query.getall(name, [])
        if not values:
            return False
        if len(values) != 1:
            return None
        value = values[0]
        normalized = value.lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
        return None

    @classmethod
    async def _read_json_object(cls, request: Request) -> tuple[dict[str, Any] | None, Response | None]:
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return None, cls._json_response(cls._bad_request("无效的 JSON 请求体"), status=400)

        if not isinstance(body, dict):
            return None, cls._json_response(cls._bad_request("JSON 请求体必须是对象"), status=400)
        return body, None

    async def _handle_health(self, _request: Request) -> Response:
        return self._json_response(
            {
                "status": "ok",
                "service": "cliany-site",
                "version": _installed_version(),
            }
        )

    async def _handle_doctor(self, request: Request) -> Response:
        llm_live = self._query_bool(request, "llm_live")
        if llm_live is None:
            return self._json_response(
                self._bad_request("llm_live 查询参数只能提供一次且必须是布尔值"),
                status=400,
            )
        require_capability_values = request.query.getall("require_capability", [])
        if len(require_capability_values) > 1:
            return self._json_response(
                self._bad_request("require_capability 查询参数只能提供一次"),
                status=400,
            )
        require_capability = (
            require_capability_values[0] if require_capability_values else None
        )
        sdk = await self._get_sdk()
        result = await sdk.doctor(
            llm_live=llm_live,
            require_capability=require_capability,
        )
        return self._json_response(result, status=self._result_status(result))

    async def _handle_list_adapters(self, request: Request) -> Response:
        detail = self._query_bool(request, "detail")
        if detail is None:
            return self._json_response(
                self._bad_request("detail 查询参数只能提供一次且必须是布尔值"),
                status=400,
            )
        sdk = await self._get_sdk()
        result = await sdk.list_adapters(detail=detail)
        return self._json_response(result)

    async def _handle_verify(self, request: Request) -> Response:
        domain_values = request.query.getall("domain", [])
        if len(domain_values) > 1:
            return self._json_response(
                self._bad_request("domain 查询参数只能提供一次"), status=400
            )
        domain = domain_values[0] if domain_values else None
        if not domain:
            return self._json_response(self._bad_request("缺少 domain 查询参数"), status=400)
        sdk = await self._get_sdk()
        result = await sdk.verify(domain)
        return self._json_response(result, status=self._result_status(result))

    async def _handle_explore(self, request: Request) -> Response:
        body, error_response = await self._read_json_object(request)
        if error_response is not None:
            return error_response
        assert body is not None

        url = self._required_string(body, "url")
        workflow = self._required_string(body, "workflow")
        if workflow is None and "workflow" not in body:
            workflow = self._required_string(body, "workflow_description")
        if url is None or workflow is None:
            return self._json_response(self._bad_request("缺少 url 或 workflow 字段"), status=400)

        force = body.get("force", False)
        if not isinstance(force, bool):
            return self._json_response(self._bad_request("force 字段必须是布尔值"), status=400)
        sdk = await self._get_sdk()
        result = await sdk.explore(url, workflow, force=force)
        return self._json_response(result, status=self._result_status(result))

    async def _handle_execute(self, request: Request) -> Response:
        body, error_response = await self._read_json_object(request)
        if error_response is not None:
            return error_response
        assert body is not None

        domain = self._required_string(body, "domain")
        command = self._required_string(body, "command")
        if domain is None or command is None:
            return self._json_response(self._bad_request("缺少 domain 或 command 字段"), status=400)

        params = body.get("params")
        if params is not None and not isinstance(params, dict):
            return self._json_response(self._bad_request("params 字段必须是 JSON 对象"), status=400)
        dry_run = body.get("dry_run", False)
        if not isinstance(dry_run, bool):
            return self._json_response(self._bad_request("dry_run 字段必须是布尔值"), status=400)
        sandbox = body.get("sandbox", False)
        if not isinstance(sandbox, bool):
            return self._json_response(self._bad_request("sandbox 字段必须是布尔值"), status=400)
        sdk = await self._get_sdk()
        result = await sdk.execute(domain, command, params=params, dry_run=dry_run, sandbox=sandbox)
        return self._json_response(result, status=self._result_status(result))

    async def _handle_login(self, request: Request) -> Response:
        body, error_response = await self._read_json_object(request)
        if error_response is not None:
            return error_response
        assert body is not None

        url = self._required_string(body, "url")
        if url is None:
            return self._json_response(self._bad_request("缺少 url 字段"), status=400)

        sdk = await self._get_sdk()
        result = await sdk.login(url)
        return self._json_response(result, status=self._result_status(result))

    def run(self) -> None:
        from aiohttp import web

        app = self._build_app()
        logger.info("启动 HTTP API 服务: %s:%d", self._host, self._port)
        web.run_app(app, host=self._host, port=self._port, print=lambda msg: logger.info(msg))
