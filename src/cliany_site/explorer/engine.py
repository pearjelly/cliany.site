import json
import importlib
import os
import re
from pathlib import Path
from typing import Any

from cliany_site.browser.axtree import capture_axtree, serialize_axtree
from cliany_site.browser.cdp import CDPConnection
from cliany_site.explorer.models import (
    ActionStep,
    CommandSuggestion,
    ExploreResult,
    PageInfo,
)
from cliany_site.explorer.prompts import EXPLORE_PROMPT_TEMPLATE, SYSTEM_PROMPT

MAX_STEPS = 10


def _load_dotenv() -> None:
    """从 .env 文件加载环境变量，不覆盖已存在的系统环境变量。

    查找顺序（后者优先级低，先查找优先级低的，后查找高优先级会覆盖低优先级）：
    1. ~/.config/cliany-site/.env（XDG 用户配置目录，最低优先级）
    2. ~/.cliany-site/.env（旧版用户配置目录，向后兼容）
    3. 项目目录 .env（项目级配置）
    4. os.environ 中已有的值保持不变（最高优先级）
    """
    try:
        from dotenv import dotenv_values
    except ImportError:
        # python-dotenv 未安装，跳过
        return

    # 收集要加载的 .env 文件，按优先级从低到高排列
    env_files: list[Path] = []

    # XDG 标准用户配置目录（最高用户优先级）
    xdg_env = (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / "cliany-site"
        / ".env"
    )
    if xdg_env.is_file():
        env_files.append(xdg_env)

    # 旧版用户配置目录（向后兼容）
    user_env = Path.home() / ".cliany-site" / ".env"
    if user_env.is_file():
        env_files.append(user_env)

    # 项目目录级别（最低优先级）
    project_env = Path.cwd() / ".env"
    if project_env.is_file():
        env_files.append(project_env)

    # 从低优先级到高优先级依次加载，后加载的覆盖前面加载的
    # 但都不覆盖已存在的 os.environ 值（系统环境变量优先级最高）
    merged: dict[str, str] = {}
    for env_file in env_files:
        values = dotenv_values(env_file)
        merged.update({k: v for k, v in values.items() if v is not None})

    # 只将 os.environ 中不存在的键写入（保证系统环境变量优先级最高）
    for key, value in merged.items():
        if key not in os.environ:
            os.environ[key] = value


def _get_llm():
    _load_dotenv()
    provider = os.environ.get("CLIANY_LLM_PROVIDER", "anthropic").lower()

    if provider == "openai":
        api_key = os.environ.get("CLIANY_OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("请设置 CLIANY_OPENAI_API_KEY 环境变量")
        model = os.environ.get("CLIANY_OPENAI_MODEL", "gpt-4o-mini")
        base_url = os.environ.get("CLIANY_OPENAI_BASE_URL")
        try:
            chat_openai = importlib.import_module("langchain_openai")
            ChatOpenAI = getattr(chat_openai, "ChatOpenAI")
            kwargs: dict = {"model": model, "temperature": 0, "api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            return ChatOpenAI(**kwargs)
        except ImportError:
            raise EnvironmentError(
                "请安装 langchain-openai: pip install langchain-openai"
            )
    else:
        # anthropic（默认），向后兼容旧环境变量 ANTHROPIC_API_KEY
        api_key = os.environ.get("CLIANY_ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_API_KEY"
        )
        if not api_key:
            raise EnvironmentError(
                "请设置 CLIANY_ANTHROPIC_API_KEY 环境变量（或旧版 ANTHROPIC_API_KEY）"
            )
        model = os.environ.get("CLIANY_ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
        base_url = os.environ.get("CLIANY_ANTHROPIC_BASE_URL")
        try:
            chat_anthropic = importlib.import_module("langchain_anthropic")
            ChatAnthropic = getattr(chat_anthropic, "ChatAnthropic")
            kwargs = {"model": model, "temperature": 0, "api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            return ChatAnthropic(**kwargs)
        except ImportError:
            raise EnvironmentError(
                "请安装 langchain-anthropic: pip install langchain-anthropic"
            )


def _parse_llm_response(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except Exception:
        return {
            "done": True,
            "actions": [],
            "commands": [],
            "reasoning": "LLM 响应解析失败",
        }


def _to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks)
    return str(content)


def _parse_ref_to_index(ref: str) -> int | None:
    if not ref:
        return None
    match = re.search(r"(\d+)", ref)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


class WorkflowExplorer:
    def __init__(self):
        self._cdp: CDPConnection | None = None

    async def explore(
        self,
        url: str,
        workflow_description: str,
        port: int = 9222,
    ) -> ExploreResult:
        result = ExploreResult()
        llm = _get_llm()

        self._cdp = CDPConnection()
        if not await self._cdp.check_available(port):
            raise ConnectionError(f"Chrome CDP 不可用 (port={port})")

        browser_session = await self._cdp.connect(port)

        try:
            await browser_session.navigate_to(url, new_tab=False)

            completed_steps: list[str] = []
            completed_steps_text = "（无）"

            for _ in range(MAX_STEPS):
                tree = await capture_axtree(browser_session)
                page_info = PageInfo(
                    url=tree.get("url", ""),
                    title=tree.get("title", ""),
                    elements=list((tree.get("selector_map") or {}).values()),
                )

                if not any(p.url == page_info.url for p in result.pages):
                    result.pages.append(page_info)

                element_tree_text = serialize_axtree(tree)
                prompt_text = EXPLORE_PROMPT_TEMPLATE.format(
                    url=tree.get("url", ""),
                    title=tree.get("title", ""),
                    element_tree=element_tree_text,
                    workflow_description=workflow_description,
                    completed_steps=completed_steps_text,
                )

                response = await llm.ainvoke(f"{SYSTEM_PROMPT}\n\n{prompt_text}")
                parsed = _parse_llm_response(_to_text(response.content))

                actions_data = parsed.get("actions", [])
                if not isinstance(actions_data, list):
                    actions_data = []

                for action_data in actions_data:
                    if not isinstance(action_data, dict):
                        continue
                    action = ActionStep(
                        action_type=action_data.get("type", "unknown"),
                        page_url=tree.get("url", ""),
                        target_ref=action_data.get("ref", ""),
                        target_url=action_data.get("url", ""),
                        value=action_data.get("value", ""),
                        description=action_data.get("description", ""),
                    )
                    result.actions.append(action)

                    description = action_data.get("description")
                    if isinstance(description, str) and description:
                        completed_steps.append(description)

                if completed_steps:
                    completed_steps_text = "\n".join(
                        f"{i + 1}. {desc}" for i, desc in enumerate(completed_steps)
                    )

                await self._execute_actions(browser_session, actions_data)

                if parsed.get("done", False):
                    commands_data = parsed.get("commands", [])
                    if not isinstance(commands_data, list):
                        commands_data = []
                    for cmd_data in commands_data:
                        if not isinstance(cmd_data, dict):
                            continue
                        args = cmd_data.get("args", [])
                        if not isinstance(args, list):
                            args = []
                        cmd = CommandSuggestion(
                            name=cmd_data.get(
                                "name", f"command-{len(result.commands) + 1}"
                            ),
                            description=cmd_data.get("description", ""),
                            args=args,
                            action_steps=list(range(len(result.actions))),
                        )
                        result.commands.append(cmd)
                    break

                next_url = parsed.get("next_url", "")
                if (
                    isinstance(next_url, str)
                    and next_url
                    and next_url != tree.get("url", "")
                ):
                    try:
                        await browser_session.navigate_to(next_url, new_tab=False)
                    except Exception:
                        pass

            if not result.commands and result.actions:
                result.commands.append(
                    CommandSuggestion(
                        name="run-workflow",
                        description=f"执行工作流: {workflow_description[:50]}",
                        args=[],
                        action_steps=list(range(len(result.actions))),
                    )
                )
        finally:
            if self._cdp is not None:
                await self._cdp.disconnect()

        return result

    async def _execute_actions(self, browser_session: Any, actions_data: list[dict]):
        from browser_use.browser.events import (
            ClickElementEvent,
            NavigateToUrlEvent,
            SelectDropdownOptionEvent,
            SendKeysEvent,
            TypeTextEvent,
        )

        for action_data in actions_data:
            if not isinstance(action_data, dict):
                continue

            try:
                action_type = action_data.get("type", "")

                if action_type == "navigate":
                    nav_url = action_data.get("url", "")
                    if isinstance(nav_url, str) and nav_url:
                        event = browser_session.event_bus.dispatch(
                            NavigateToUrlEvent(
                                url=nav_url,
                                wait_until="domcontentloaded",
                                new_tab=False,
                            )
                        )
                        await event
                        await event.event_result(
                            raise_if_any=False, raise_if_none=False
                        )
                    continue

                if action_type == "submit":
                    event = browser_session.event_bus.dispatch(
                        SendKeysEvent(keys="Enter")
                    )
                    await event
                    await event.event_result(raise_if_any=False, raise_if_none=False)
                    continue

                ref = action_data.get("ref", "")
                if not isinstance(ref, str):
                    continue
                element_index = _parse_ref_to_index(ref)
                if element_index is None:
                    continue

                node = await browser_session.get_element_by_index(element_index)
                if node is None:
                    continue

                if action_type == "click":
                    event = browser_session.event_bus.dispatch(
                        ClickElementEvent(node=node)
                    )
                    await event
                    await event.event_result(raise_if_any=False, raise_if_none=False)
                elif action_type == "type":
                    value = action_data.get("value", "")
                    if isinstance(value, str):
                        event = browser_session.event_bus.dispatch(
                            TypeTextEvent(node=node, text=value, clear=True)
                        )
                        await event
                        await event.event_result(
                            raise_if_any=False, raise_if_none=False
                        )
                elif action_type == "select":
                    value = action_data.get("value", "")
                    if isinstance(value, str) and value:
                        event = browser_session.event_bus.dispatch(
                            SelectDropdownOptionEvent(node=node, text=value)
                        )
                        await event
                        await event.event_result(
                            raise_if_any=False, raise_if_none=False
                        )
            except Exception:
                pass
