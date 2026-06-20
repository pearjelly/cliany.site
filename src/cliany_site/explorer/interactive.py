from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

import click
from rich.console import Console
from rich.panel import Panel

from cliany_site.browser.axtree import capture_axtree

if TYPE_CHECKING:
    from cliany_site.explorer.models import ExploreResult, TurnSnapshot


logger = logging.getLogger(__name__)


class DecisionType(Enum):
    CONFIRM = "confirm"
    SKIP = "skip"
    MODIFY = "modify"
    ROLLBACK = "rollback"


@dataclass
class InteractiveDecision:
    decision_type: DecisionType
    field: str | None = None
    new_value: str | None = None


class InteractiveController:
    ALLOWED_MODIFY_FIELDS = {"value", "ref"}

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def _check_tty(self):
        if not sys.stdin.isatty():
            raise click.UsageError("--interactive 需要 TTY 终端，无法在管道/非交互环境运行")

    def _get_input(self, prompt: str) -> str:
        return input(prompt).strip()

    async def _async_input(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        return (await loop.run_in_executor(None, input, prompt)).strip()

    async def prompt_action_confirmation(
        self,
        actions: list,
        page_summary: str = "",
    ) -> InteractiveDecision:
        self._check_tty()

        self.console.print(
            Panel(
                f"页面: {page_summary}\n提议动作数量: {len(actions)}",
                title="交互确认",
                border_style="blue",
            )
        )

        while True:
            choice = await self._async_input("操作 [1/y=确认, 2/s=跳过, 3/m=修改, 4/b=回退]: ")

            if choice.lower() in ("1", "y", "confirm", "yes", "确认"):
                return InteractiveDecision(decision_type=DecisionType.CONFIRM)

            elif choice.lower() in ("2", "s", "skip", "跳过"):
                return InteractiveDecision(decision_type=DecisionType.SKIP)

            elif choice.lower() in ("3", "m", "modify", "修改"):
                return await self._handle_modify()

            elif choice.lower() in ("4", "b", "rollback", "回退"):
                return InteractiveDecision(decision_type=DecisionType.ROLLBACK)

            else:
                self.console.print(f"[red]无效输入 '{choice}'，请重新输入[/red]")

    async def _handle_modify(self) -> InteractiveDecision:
        while True:
            field = await self._async_input(f"要修改的字段 ({'/'.join(sorted(self.ALLOWED_MODIFY_FIELDS))}): ")
            if field in self.ALLOWED_MODIFY_FIELDS:
                break
            self.console.print(f"[red]只能修改: {self.ALLOWED_MODIFY_FIELDS}[/red]")

        new_value = await self._async_input(f"新的 {field} 值: ")
        return InteractiveDecision(
            decision_type=DecisionType.MODIFY,
            field=field,
            new_value=new_value,
        )

    @staticmethod
    def _extract_history_data(history: Any) -> tuple[int | None, list[Any]]:
        if isinstance(history, dict):
            current_index = history.get("currentIndex")
            entries = history.get("entries")
        else:
            current_index = getattr(history, "currentIndex", None)
            entries = getattr(history, "entries", None)

        if not isinstance(entries, list):
            entries = []
        if not isinstance(current_index, int):
            current_index = None
        return current_index, entries

    @staticmethod
    def _extract_history_entry_id(entry: Any) -> int | None:
        entry_id = entry.get("id") if isinstance(entry, dict) else getattr(entry, "id", None)
        return entry_id if isinstance(entry_id, int) else None

    async def _try_browser_back(self, browser_session: Any, fallback_url: str) -> None:
        session_id: str | None = None
        try:
            get_session = getattr(browser_session, "get_or_create_cdp_session", None)
            if callable(get_session):
                maybe_session = get_session()
                if asyncio.iscoroutine(maybe_session):
                    cdp_session = await maybe_session
                else:
                    cdp_session = maybe_session
                maybe_session_id = getattr(cdp_session, "session_id", None)
                session_id = str(maybe_session_id) if maybe_session_id else None
        except (TimeoutError, AttributeError, RuntimeError) as exc:
            logger.warning(
                "获取 CDP session 失败，将继续尝试回退: %s",
                exc,
                extra={"step": "get_cdp_session", "url": fallback_url},
            )

        cdp_client = getattr(browser_session, "cdp_client", None)
        send_api = getattr(cdp_client, "send", None)
        page_api = getattr(send_api, "Page", None)

        used_history_back = False
        if page_api is not None and callable(getattr(page_api, "getNavigationHistory", None)):
            used_history_back = True
            history = await page_api.getNavigationHistory(session_id=session_id)
            current_index, entries = self._extract_history_data(history)
            if current_index is not None and current_index > 0 and current_index <= len(entries) - 1:
                previous_entry = entries[current_index - 1]
                entry_id = self._extract_history_entry_id(previous_entry)
                if entry_id is not None:
                    await page_api.navigateToHistoryEntry({"entryId": entry_id}, session_id=session_id)
                    return
            logger.warning("浏览器历史回退不可用：未找到上一个 history entry")

        if fallback_url:
            if page_api is not None and callable(getattr(page_api, "navigate", None)):
                await page_api.navigate({"url": fallback_url}, session_id=session_id)
                return

            navigate_to = getattr(browser_session, "navigate_to", None)
            if callable(navigate_to):
                maybe_navigate = navigate_to(fallback_url, new_tab=False)
                if asyncio.iscoroutine(maybe_navigate):
                    await maybe_navigate
                return

        if used_history_back:
            logger.warning("浏览器回退失败：history back 与 fallback 导航均未生效")
        else:
            logger.warning("浏览器回退失败：CDP Page.getNavigationHistory 不可用且 fallback 导航不可用")

    async def handle_rollback(
        self,
        snapshot: TurnSnapshot,
        result: ExploreResult,
        browser_session,
        recording_manager=None,
        recording_manifest=None,
    ) -> bool:
        if snapshot.actions_before_count == 0:
            self.console.print("[yellow]已在第一步，无法回退[/yellow]")
            logger.info("回退请求被拒绝：已在第一步")
            return False

        fallback_url = ""
        if snapshot.pages_before_count > 0 and snapshot.pages_before_count <= len(result.pages):
            fallback_url = result.pages[snapshot.pages_before_count - 1].url

        result.actions = result.actions[: snapshot.actions_before_count]
        result.pages = result.pages[: snapshot.pages_before_count]

        try:
            await self._try_browser_back(browser_session, fallback_url)
        except (TimeoutError, ConnectionError, RuntimeError, OSError) as exc:
            logger.warning(
                "执行浏览器回退失败（继续流程）: %s",
                exc,
                extra={"step": "browser_back", "url": fallback_url},
            )

        try:
            await capture_axtree(browser_session)
        except Exception as exc:
            logger.warning(
                "回退后 AXTree 捕获失败（继续流程）: %s",
                exc,
                extra={"step": "capture_axtree", "url": fallback_url},
            )

        if recording_manager is not None and recording_manifest is not None:
            try:
                recording_manager.mark_rolled_back(recording_manifest, snapshot.turn_index)
            except Exception as exc:
                logger.warning(
                    "标记录像回退步骤失败（继续流程）: %s",
                    exc,
                    extra={"step": "mark_rolled_back", "url": fallback_url},
                )

        return True
