# ---------------------------------------------------------------------------
# cliany-site Python SDK — 程序化调用接口
# ---------------------------------------------------------------------------
"""cliany-site 的 Python SDK，支持同步和异步调用。

用法示例::

    # 同步便捷函数
    from cliany_site.sdk import explore, execute, doctor, list_adapters

    result = doctor()
    adapters = list_adapters()

    # 异步上下文管理器
    from cliany_site.sdk import ClanySite

    async with ClanySite() as cs:
        result = await cs.explore("https://github.com", "搜索仓库")
        adapters = await cs.list_adapters()
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlparse

from cliany_site.config import get_config
from cliany_site.errors import (
    CDP_UNAVAILABLE,
    EXECUTION_FAILED,
    EXPLORE_FAILED,
    LLM_UNAVAILABLE,
    CdpError,
)
from cliany_site.response import error_response, success_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 核心异步上下文管理器
# ---------------------------------------------------------------------------


class ClanySite:
    """cliany-site 的异步 SDK 入口。

    用法::

        async with ClanySite() as cs:
            result = await cs.explore("https://github.com", "搜索仓库")
            info = await cs.doctor()
            adapters = await cs.list_adapters()

    参数:
        cdp_url: 自定义 CDP 连接地址（如 ``ws://host:9222``）
        headless: 是否以 Headless 模式启动 Chrome
        port: CDP 端口号（默认 9222）
    """

    def __init__(
        self,
        cdp_url: str | None = None,
        headless: bool | None = None,
        port: int | None = None,
    ) -> None:
        self._cdp_url = cdp_url
        self._headless = headless
        self._port = port
        self._cdp: Any = None
        self._session: Any = None

    async def __aenter__(self) -> ClanySite:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """释放 CDP 连接和浏览器资源。"""
        if self._cdp is not None:
            await self._cdp.disconnect()
            self._cdp = None
            self._session = None

    async def _ensure_cdp(self) -> Any:
        """确保 CDP 连接可用并返回 CDPConnection 实例。"""
        if self._cdp is None:
            from cliany_site.browser.cdp import CDPConnection

            self._cdp = CDPConnection(cdp_url=self._cdp_url, headless=self._headless)
        return self._cdp

    async def _ensure_browser_session(self) -> Any:
        """确保浏览器会话已建立并返回 BrowserSession 实例。"""
        cdp = await self._ensure_cdp()
        if self._session is None:
            port = self._port or get_config().cdp_port
            if not await cdp.check_available(port):
                raise CdpError(f"Chrome CDP 不可用 (port={port})")
            self._session = await cdp.connect(port)
        return self._session

    # ── explore ──────────────────────────────────────────

    async def explore(
        self,
        url: str,
        workflow_description: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """探索网站工作流并生成 CLI adapter。

        Args:
            url: 目标网站 URL
            workflow_description: 工作流描述（中文或英文）
            force: 是否强制覆盖已有 adapter

        Returns:
            标准信封格式 ``{"success": bool, "data": {...}, "error": ...}``
        """
        from cliany_site.codegen.generator import AdapterGenerator, _safe_domain, save_adapter
        from cliany_site.codegen.merger import AdapterMerger
        from cliany_site.explorer.engine import WorkflowExplorer

        try:
            explorer = WorkflowExplorer(
                cdp_url=self._cdp_url,
                headless=self._headless,
            )
            explore_result = await explorer.explore(url, workflow_description, port=self._port)
        except ConnectionError as e:
            return error_response(CDP_UNAVAILABLE, str(e), "请确保 Chrome CDP 可用")
        except OSError as e:
            if "API" in str(e) or "Key" in str(e):
                return error_response(LLM_UNAVAILABLE, str(e))
            return error_response(EXPLORE_FAILED, str(e))
        except (RuntimeError, ValueError) as e:
            return error_response(EXPLORE_FAILED, f"探索失败: {e}")

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        adapter_dir = get_config().adapters_dir / _safe_domain(domain)

        if force or not adapter_dir.exists():
            gen = AdapterGenerator()
            code = gen.generate(explore_result, domain)
            metadata = {"source_url": url, "workflow": workflow_description}
            adapter_path = save_adapter(domain, code, metadata, explore_result=explore_result)
            commands_list = [cmd.name for cmd in explore_result.commands]
            return success_response(
                {
                    "domain": domain,
                    "adapter_path": adapter_path,
                    "adapter_mode": "created",
                    "commands": commands_list,
                    "commands_count": len(commands_list),
                    "pages_explored": len(explore_result.pages),
                    "actions_found": len(explore_result.actions),
                }
            )
        else:
            merger = AdapterMerger(domain)
            merge_result = merger.merge(explore_result, json_mode=True, workflow=workflow_description)
            commands_list = [cmd.get("name", "") for cmd in merge_result.merged]
            adapter_path = str(merger.metadata_path.parent / "commands.py")
            return success_response(
                {
                    "domain": domain,
                    "adapter_path": adapter_path,
                    "adapter_mode": "merged",
                    "commands": commands_list,
                    "commands_added": merge_result.added_count,
                    "commands_total": merge_result.total_count,
                    "pages_explored": len(explore_result.pages),
                    "actions_found": len(explore_result.actions),
                }
            )

    # ── execute ──────────────────────────────────────────

    async def execute(
        self,
        domain: str,
        command: str,
        *,
        params: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """执行指定域名 adapter 中的命令。

        Args:
            domain: 网站域名（如 ``github.com``）
            command: 命令名称（如 ``search``）
            params: 命令参数字典
            dry_run: 是否仅验证而不真正执行

        Returns:
            标准信封格式
        """
        from cliany_site.action_runtime import execute_action_steps
        from cliany_site.session import load_session

        cfg = get_config()
        metadata_path = cfg.adapters_dir / domain / "metadata.json"
        if not metadata_path.exists():
            return error_response(
                "ADAPTER_NOT_FOUND",
                f"未找到 adapter: {domain}",
                "请先运行 explore 生成 adapter",
            )

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            return error_response(EXECUTION_FAILED, f"读取 adapter 元数据失败: {e}")

        command_defs = metadata.get("command_defs", [])
        cmd_def = None
        for cd in command_defs:
            if cd.get("name") == command:
                cmd_def = cd
                break

        if cmd_def is None:
            available = [cd.get("name", "") for cd in command_defs]
            return error_response(
                "COMMAND_NOT_FOUND",
                f"adapter '{domain}' 中未找到命令 '{command}'",
                f"可用命令: {', '.join(available)}" if available else "该 adapter 无可用命令",
            )

        actions_data = cmd_def.get("actions", [])
        if not actions_data:
            return error_response(
                EXECUTION_FAILED,
                f"命令 '{command}' 没有录制的操作步骤",
            )

        browser_session = await self._ensure_browser_session()

        try:
            await load_session(domain, browser_session)
        except (OSError, RuntimeError, ValueError):
            logger.debug("加载 session 失败，继续执行: domain=%s", domain)

        try:
            await execute_action_steps(
                browser_session,
                actions_data,
                continue_on_error=False,
                params=params,
                domain=domain,
                command_name=command,
                dry_run=dry_run,
            )
            return success_response(
                {
                    "domain": domain,
                    "command": command,
                    "actions_executed": len(actions_data),
                    "dry_run": dry_run,
                    "status": "completed",
                }
            )
        except Exception as e:
            return error_response(
                EXECUTION_FAILED,
                f"执行失败: {e}",
                "请检查 Chrome 状态或重新 explore",
            )

    # ── login ────────────────────────────────────────────

    async def login(self, url: str) -> dict[str, Any]:
        """程序化登录 — 从当前浏览器捕获 Session。

        注意：此方法假设用户已在 Chrome 中完成登录操作。
        不同于 CLI 的 ``login`` 命令，SDK 版不会暂停等待用户输入。

        Args:
            url: 目标网站 URL

        Returns:
            标准信封格式，含 session_file 和 cookies_count
        """
        from cliany_site.session import save_session

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if not domain:
            return error_response("INVALID_URL", f"无法从 URL 提取 domain: {url}")

        browser_session = await self._ensure_browser_session()

        try:
            try:
                await browser_session.navigate_to(url, new_tab=False)
            except (OSError, RuntimeError):
                logger.debug("导航到 %s 失败，尝试直接捕获当前页面 session", url)

            path, cookies_count = await save_session(domain, browser_session)

            if cookies_count == 0:
                return error_response(
                    "NO_COOKIES",
                    f"未从 {domain} 获取到任何 Cookie",
                    "请确认已在 Chrome 中完成登录",
                )

            return success_response(
                {
                    "domain": domain,
                    "session_file": path,
                    "cookies_count": cookies_count,
                }
            )
        except (OSError, RuntimeError, ValueError) as e:
            return error_response(EXECUTION_FAILED, f"Session 捕获失败: {e}")

    # ── doctor ───────────────────────────────────────────

    async def doctor(self) -> dict[str, Any]:
        """检查运行环境（CDP / LLM / 目录）。

        Returns:
            标准信封格式，data 中包含各项检查结果
        """
        import os

        from cliany_site.explorer.engine import _load_dotenv, _normalize_openai_base_url

        _load_dotenv()

        checks: dict[str, Any] = {}
        cfg = get_config()

        try:
            cdp = await self._ensure_cdp()
            port = self._port or cfg.cdp_port
            checks["cdp"] = "ok" if await cdp.check_available(port) else "fail"
        except (OSError, RuntimeError, TimeoutError):
            checks["cdp"] = "fail"

        has_llm = bool(
            os.environ.get("CLIANY_ANTHROPIC_API_KEY")
            or os.environ.get("CLIANY_OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
        )
        checks["llm"] = "ok" if has_llm else "fail"

        provider = os.environ.get("CLIANY_LLM_PROVIDER", "anthropic").lower()
        checks["llm_provider"] = "ok" if provider in {"anthropic", "openai"} else "fail"

        if provider == "openai":
            base_url = os.environ.get("CLIANY_OPENAI_BASE_URL")
            try:
                normalized = _normalize_openai_base_url(base_url)
                checks["openai_base_url"] = "ok" if (normalized or not base_url) else "fail"
            except (ValueError, TypeError):
                checks["openai_base_url"] = "fail"

        checks["adapters_dir"] = "ok" if cfg.adapters_dir.exists() else "fail"
        checks["sessions_dir"] = "ok" if cfg.sessions_dir.exists() else "fail"
        checks["config"] = cfg.to_dict()

        failed = [k for k, v in checks.items() if v == "fail"]
        if failed:
            return error_response(
                "DOCTOR_ISSUES",
                f"以下检查项失败: {', '.join(failed)}",
                "请检查 Chrome CDP 和 LLM API key",
            ) | {"data": checks}

        return success_response(checks)

    # ── list_adapters ────────────────────────────────────

    async def list_adapters(self, detail: bool = False) -> dict[str, Any]:
        """列出所有已安装的 adapter。

        Args:
            detail: 是否包含详细元数据

        Returns:
            标准信封格式，data 中包含 adapters 列表
        """
        from cliany_site.loader import discover_adapters

        adapters = discover_adapters()

        if detail:
            return success_response({"adapters": adapters})

        return success_response(
            {
                "adapters": [a["domain"] for a in adapters],
                "count": len(adapters),
            }
        )

    # ── save_session ─────────────────────────────────────

    async def save_session(self, domain: str) -> dict[str, Any]:
        """保存当前浏览器的 Session 数据。

        Args:
            domain: 网站域名

        Returns:
            标准信封格式
        """
        from cliany_site.session import save_session as _save

        browser_session = await self._ensure_browser_session()
        try:
            path, count = await _save(domain, browser_session)
            return success_response(
                {
                    "domain": domain,
                    "session_file": path,
                    "cookies_count": count,
                }
            )
        except (OSError, RuntimeError, ValueError) as e:
            return error_response(EXECUTION_FAILED, f"Session 保存失败: {e}")

    # ── navigate ─────────────────────────────────────────

    async def navigate(self, url: str) -> dict[str, Any]:
        """在浏览器中导航到指定 URL。

        Args:
            url: 目标 URL

        Returns:
            标准信封格式
        """
        browser_session = await self._ensure_browser_session()
        try:
            await browser_session.navigate_to(url, new_tab=False)
            return success_response({"url": url, "status": "navigated"})
        except (OSError, RuntimeError, TimeoutError) as e:
            return error_response(EXECUTION_FAILED, f"导航失败: {e}")

    # ── get_page_info ────────────────────────────────────

    async def get_page_info(self) -> dict[str, Any]:
        """获取当前页面信息（URL、标题、AXTree 元素数量）。

        Returns:
            标准信封格式
        """
        from cliany_site.browser.axtree import capture_axtree

        browser_session = await self._ensure_browser_session()
        try:
            tree = await capture_axtree(browser_session)
            selector_map = tree.get("selector_map", {})
            return success_response(
                {
                    "url": tree.get("url", ""),
                    "title": tree.get("title", ""),
                    "elements_count": len(selector_map),
                }
            )
        except (OSError, RuntimeError) as e:
            return error_response(EXECUTION_FAILED, f"获取页面信息失败: {e}")


# ---------------------------------------------------------------------------
# 同步便捷函数
# ---------------------------------------------------------------------------


def _run_async(coro: Any) -> dict[str, Any]:
    """在新事件循环中运行协程。如果已有事件循环，使用 nest_asyncio 或创建新线程。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        result: dict[str, Any] = future.result()
        return result


def explore(
    url: str,
    workflow_description: str,
    *,
    force: bool = False,
    cdp_url: str | None = None,
    headless: bool | None = None,
) -> dict[str, Any]:
    """同步版: 探索网站工作流并生成 adapter。

    Args:
        url: 目标网站 URL
        workflow_description: 工作流描述
        force: 是否强制覆盖已有 adapter
        cdp_url: 自定义 CDP 连接地址
        headless: 是否 Headless 模式

    Returns:
        标准信封格式

    示例::

        from cliany_site.sdk import explore
        result = explore("https://github.com", "搜索仓库并查看 README")
        if result["success"]:
            print(result["data"]["commands"])
    """

    async def _inner() -> dict[str, Any]:
        async with ClanySite(cdp_url=cdp_url, headless=headless) as cs:
            return await cs.explore(url, workflow_description, force=force)

    return _run_async(_inner())


def execute(
    domain: str,
    command: str,
    *,
    params: dict[str, Any] | None = None,
    dry_run: bool = False,
    cdp_url: str | None = None,
    headless: bool | None = None,
) -> dict[str, Any]:
    """同步版: 执行指定 adapter 命令。

    Args:
        domain: 网站域名
        command: 命令名称
        params: 命令参数
        dry_run: 是否仅验证
        cdp_url: 自定义 CDP 连接地址
        headless: 是否 Headless 模式

    Returns:
        标准信封格式

    示例::

        from cliany_site.sdk import execute
        result = execute("github.com", "search", params={"query": "cliany"})
    """

    async def _inner() -> dict[str, Any]:
        async with ClanySite(cdp_url=cdp_url, headless=headless) as cs:
            return await cs.execute(domain, command, params=params, dry_run=dry_run)

    return _run_async(_inner())


def login(
    url: str,
    *,
    cdp_url: str | None = None,
    headless: bool | None = None,
) -> dict[str, Any]:
    """同步版: 从浏览器捕获 Session。

    Args:
        url: 目标网站 URL
        cdp_url: 自定义 CDP 连接地址
        headless: 是否 Headless 模式

    Returns:
        标准信封格式
    """

    async def _inner() -> dict[str, Any]:
        async with ClanySite(cdp_url=cdp_url, headless=headless) as cs:
            return await cs.login(url)

    return _run_async(_inner())


def doctor(
    *,
    cdp_url: str | None = None,
    headless: bool | None = None,
) -> dict[str, Any]:
    """同步版: 检查运行环境。

    Returns:
        标准信封格式
    """

    async def _inner() -> dict[str, Any]:
        async with ClanySite(cdp_url=cdp_url, headless=headless) as cs:
            return await cs.doctor()

    return _run_async(_inner())


def list_adapters(detail: bool = False) -> dict[str, Any]:
    """同步版: 列出所有已安装的 adapter。

    Args:
        detail: 是否返回详细元数据

    Returns:
        标准信封格式
    """

    async def _inner() -> dict[str, Any]:
        async with ClanySite() as cs:
            return await cs.list_adapters(detail=detail)

    return _run_async(_inner())
