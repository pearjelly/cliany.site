import asyncio
import contextlib
import importlib
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import click

from cliany_site.action_runtime import execute_action_steps, normalize_navigation_url
from cliany_site.browser.axtree import capture_axtree, serialize_axtree
from cliany_site.browser.cdp import CDPConnection
from cliany_site.browser.screenshot import capture_screenshot
from cliany_site.browser.selector import format_selector_candidates_section
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.config import get_config
from cliany_site.explorer.models import (
    ActionStep,
    CommandSuggestion,
    ExploreResult,
    PageInfo,
    StepRecord,
    TurnSnapshot,
)
from cliany_site.explorer.prompts import (
    EXPLORE_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
    build_atom_inventory_section,
)
from cliany_site.extract_writer import save_extract_markdown
from cliany_site.progress import NullProgressReporter, ProgressReporter

logger = logging.getLogger(__name__)


def _to_snake_case(value: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized.lower()


def _infer_name_from_description(description: str) -> str:
    mapping: list[tuple[tuple[str, ...], str]] = [
        (("标题",), "title"),
        (("内容", "正文", "描述"), "body"),
        (("搜索", "关键词", "查询"), "query"),
        (("名称", "名字"), "name"),
        (("地址", "网址", "url"), "url"),
    ]

    for keywords, inferred_name in mapping:
        if any(keyword in description for keyword in keywords):
            return inferred_name
    return ""


_GENERIC_COMMAND_NAMES = frozenset(
    {
        "run-workflow",
        "run_workflow",
        "workflow",
        "command",
        "command-1",
    }
)


def _infer_command_name_from_description(description: str) -> str:
    mapping: list[tuple[tuple[str, ...], str]] = [
        (
            (
                "创建issue",
                "创建 issue",
                "新建issue",
                "新建 issue",
                "提交issue",
                "提交 issue",
                "提issue",
                "提 issue",
                "create issue",
            ),
            "create-issue",
        ),
        (("搜索", "查找", "search"), "search"),
        (("登录", "login", "sign in"), "login"),
        (("注册", "signup", "sign up"), "register"),
        (("删除", "delete", "remove"), "delete"),
        (("编辑", "修改", "edit", "update"), "edit"),
        (("查看", "浏览", "view"), "view"),
        (("下载", "download"), "download"),
        (("上传", "upload"), "upload"),
        (("发布", "publish"), "publish"),
        (("评论", "comment"), "comment"),
        (("提交", "submit"), "submit"),
    ]
    desc_lower = description.lower()

    # 取最后出现的关键词匹配 —— 描述末尾的动作通常是最终意图
    best_name = ""
    best_pos = -1
    for keywords, inferred_name in mapping:
        for kw in keywords:
            pos = desc_lower.rfind(kw)
            if pos != -1 and pos > best_pos:
                best_pos = pos
                best_name = inferred_name
    return best_name


def _infer_params_from_actions(
    actions: list,
    workflow_description: str,
) -> list[dict]:
    _ = workflow_description
    inferred_args: list[dict] = []
    seen_names: set[str] = set()

    for action_index, action in enumerate(actions):
        if len(inferred_args) >= 5:
            break

        action_type = str(getattr(action, "action_type", "") or "").lower()
        if action_type != "type":
            continue

        value = str(getattr(action, "value", "") or "").strip()
        if not value:
            continue

        raw_description = str(getattr(action, "description", "") or "")
        target_name = str(getattr(action, "target_name", "") or "").strip()

        param_name = _to_snake_case(target_name) if target_name else ""
        if not param_name and raw_description.strip():
            param_name = _infer_name_from_description(raw_description)
        if not param_name:
            param_name = f"input_{action_index}"

        if param_name in seen_names:
            continue
        seen_names.add(param_name)

        inferred_args.append(
            {
                "name": param_name,
                "description": raw_description,
                "required": True,
                "action_index": action_index,
                "default": value,
            }
        )

    return inferred_args


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
    xdg_env = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "cliany-site" / ".env"
    if xdg_env.is_file():
        env_files.append(xdg_env)

    # 旧版用户配置目录（向后兼容）
    user_env = get_config().home_dir / ".env"
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


def _normalize_openai_base_url(base_url: str | None) -> str | None:
    if not isinstance(base_url, str):
        return None

    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise OSError("CLIANY_OPENAI_BASE_URL 格式无效，请使用 http(s)://host[:port][/v1]")

    path = parsed.path.rstrip("/")
    if path in {"", "/"}:
        return f"{normalized}/v1"
    return normalized


def _get_llm(role: str = "explore"):
    _load_dotenv()

    # 双模型支持：录制阶段用 EXPLORE 环境变量，回放阶段用 REPLAY 环境变量
    # 若对应 role 的变量未设置，则回退到通用变量
    role_upper = role.upper()

    provider = (
        os.environ.get(f"CLIANY_{role_upper}_LLM_PROVIDER") or os.environ.get("CLIANY_LLM_PROVIDER", "anthropic")
    ).lower()

    if provider == "openai":
        api_key = os.environ.get(f"CLIANY_{role_upper}_OPENAI_API_KEY") or os.environ.get("CLIANY_OPENAI_API_KEY")
        if not api_key:
            raise OSError("请设置 CLIANY_OPENAI_API_KEY 环境变量")
        model = os.environ.get(f"CLIANY_{role_upper}_OPENAI_MODEL") or os.environ.get(
            "CLIANY_OPENAI_MODEL", "gpt-4o-mini"
        )
        base_url = _normalize_openai_base_url(
            os.environ.get(f"CLIANY_{role_upper}_OPENAI_BASE_URL") or os.environ.get("CLIANY_OPENAI_BASE_URL")
        )
        try:
            chat_openai = importlib.import_module("langchain_openai")
            ChatOpenAI = chat_openai.ChatOpenAI
            kwargs: dict = {"model": model, "temperature": 0, "api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url

            json_mode_kwargs = dict(kwargs)
            json_mode_kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
            try:
                return ChatOpenAI(**json_mode_kwargs)
            except (TypeError, ValueError):
                return ChatOpenAI(**kwargs)
        except ImportError as exc:
            raise OSError("请安装 langchain-openai: pip install langchain-openai") from exc
    elif provider == "anthropic":
        api_key = (
            os.environ.get(f"CLIANY_{role_upper}_ANTHROPIC_API_KEY")
            or os.environ.get("CLIANY_ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        if not api_key:
            raise OSError("请设置 CLIANY_ANTHROPIC_API_KEY 环境变量（或旧版 ANTHROPIC_API_KEY）")
        model = os.environ.get(f"CLIANY_{role_upper}_ANTHROPIC_MODEL") or os.environ.get(
            "CLIANY_ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"
        )
        base_url = os.environ.get(f"CLIANY_{role_upper}_ANTHROPIC_BASE_URL") or os.environ.get(
            "CLIANY_ANTHROPIC_BASE_URL"
        )
        try:
            chat_anthropic = importlib.import_module("langchain_anthropic")
            ChatAnthropic = chat_anthropic.ChatAnthropic
            kwargs = {"model": model, "temperature": 0, "api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            return ChatAnthropic(**kwargs)
        except ImportError as exc:
            raise OSError("请安装 langchain-anthropic: pip install langchain-anthropic") from exc

    raise OSError("CLIANY_LLM_PROVIDER 仅支持 anthropic 或 openai")


def _get_replay_llm():
    return _get_llm(role="replay")


def _parse_llm_response(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        result: dict[Any, Any] = json.loads(text)
        return result
    except (json.JSONDecodeError, ValueError):
        return {
            "done": True,
            "actions": [],
            "commands": [],
            "reasoning": "LLM 响应解析失败",
        }


_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _is_retryable_error(exc: Exception) -> bool:
    for target in (exc, exc.__cause__):
        if target is None:
            continue
        status_code = getattr(target, "status_code", None)
        if isinstance(status_code, int) and status_code in _RETRYABLE_STATUS_CODES:
            return True
    return False


async def _invoke_llm_with_retry(
    llm: Any,
    prompt: Any,
    *,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
) -> Any:
    """带指数退避重试的 LLM 调用。支持纯文本和多模态消息。"""
    for attempt in range(max_attempts):
        try:
            if isinstance(prompt, str):
                return await llm.ainvoke(prompt)
            else:
                messages = [prompt] if not isinstance(prompt, list) else prompt
                return await llm.ainvoke(messages)
        except Exception as exc:
            if not _is_retryable_error(exc) or attempt >= max_attempts - 1:
                raise
            delay = base_delay * (backoff_factor**attempt)
            logger.warning(
                "LLM 调用失败 (第 %d/%d 次): %s — %.1f 秒后重试",
                attempt + 1,
                max_attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("LLM 重试逻辑异常")


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


def _sanitize_actions_data(actions_data: Any, current_url: str) -> list[dict[str, Any]]:
    if not isinstance(actions_data, list):
        return []

    sanitized: list[dict[str, Any]] = []
    for action_data in actions_data:
        if not isinstance(action_data, dict):
            continue

        normalized = dict(action_data)
        action_type = str(normalized.get("type", "")).lower()
        if action_type == "input":
            action_type = "type"
        if action_type:
            normalized["type"] = action_type

        # value 字段归一化：LLM 可能用 text/content/query/keyword 代替 value
        current_value = str(normalized.get("value", "") or "").strip()
        if not current_value:
            for alt_key in ("text", "content", "query", "keyword", "input"):
                alt_value = str(normalized.get(alt_key, "") or "").strip()
                if alt_value:
                    normalized["value"] = alt_value
                    break

        if action_type == "navigate":
            nav_url = normalize_navigation_url(normalized.get("url", ""), current_url)
            if not nav_url:
                continue
            normalized["url"] = nav_url

        if action_type == "extract" and not str(normalized.get("selector", "") or "").strip():
            logger.warning(
                "extract 动作的 selector 为空，可能无法提取数据: %s",
                normalized.get("description", ""),
            )
        sanitized.append(normalized)

    return sanitized


def load_existing_adapter_context(domain: str) -> dict:
    """加载已有适配器的 metadata.json，返回命令上下文摘要。

    Args:
        domain: 域名，如 "github.com"

    Returns:
        包含命令摘要的字典

    Raises:
        FileNotFoundError: 若该 domain 的适配器不存在
    """
    adapter_path = Path.home() / ".cliany-site" / "adapters" / domain / "metadata.json"
    if not adapter_path.exists():
        raise FileNotFoundError(f"域名 '{domain}' 的适配器不存在: {adapter_path}")

    with adapter_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    commands = metadata.get("commands", [])
    context: dict = {
        "domain": domain,
        "existing_commands": [],
    }

    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        cmd_summary = {
            "name": cmd.get("name", ""),
            "description": cmd.get("description", ""),
            "args": [
                {"name": a.get("name", ""), "description": a.get("description", "")}
                for a in (cmd.get("args") or [])
                if isinstance(a, dict)
            ],
        }
        context["existing_commands"].append(cmd_summary)

    return context


class WorkflowExplorer:
    def __init__(
        self,
        cdp_url: str | None = None,
        headless: bool | None = None,
        extend_domain: str | None = None,
        interactive: bool = False,
    ):
        self._cdp: CDPConnection | None = None
        self._cdp_url = cdp_url
        self._headless = headless
        self._interactive = interactive
        self._extend_context: dict | None = None
        if extend_domain is not None:
            # 快速失败：在初始化时验证 domain 存在
            self._extend_context = load_existing_adapter_context(extend_domain)

    async def explore(
        self,
        url: str,
        workflow_description: str,
        port: int | None = None,
        progress: ProgressReporter | None = None,
        record: bool = True,
    ) -> ExploreResult:
        cfg = get_config()
        if port is None:
            port = cfg.cdp_port
        reporter: ProgressReporter = progress or NullProgressReporter()
        explore_start = time.monotonic()
        logger.info("开始探索: url=%s workflow=%s", url, workflow_description)

        result = ExploreResult()
        llm = _get_llm(role="explore")
        result.explore_model = getattr(llm, "model", None) or getattr(llm, "model_name", None) or ""
        logger.debug("LLM provider=%s model=%s", type(llm).__name__, result.explore_model)

        self._cdp = CDPConnection(cdp_url=self._cdp_url, headless=self._headless)
        if not await self._cdp.check_available(port):
            raise ConnectionError(f"Chrome CDP 不可用 (port={port})")

        browser_session = await self._cdp.connect(port)
        domain = urlparse(url).netloc or "unknown"

        recording_manifest = None
        recording_manager = None
        if record:
            try:
                from cliany_site.explorer.recording import RecordingManager

                session_id = f"sess-{int(time.time() * 1000)}"
                recording_manager = RecordingManager()
                recording_manifest = recording_manager.start_recording(
                    domain,
                    url,
                    workflow_description,
                    session_id,
                )
            except Exception as e:
                logger.warning(f"录像初始化失败，将跳过录像: {e}")

        interactive_ctrl = None
        if self._interactive:
            from cliany_site.explorer.interactive import InteractiveController

            interactive_ctrl = InteractiveController()

        explore_completed = False
        _recording_finalized = False

        try:
            await browser_session.navigate_to(url, new_tab=False)
            reporter.on_explore_start(url, workflow_description, cfg.explore_max_steps)

            completed_steps: list[str] = []
            completed_steps_text = "（无）"
            final_step_count = 0
            all_extraction_results: list = []

            for step_num in range(cfg.explore_max_steps):
                step_start = time.monotonic()
                reporter.on_explore_step_start(step_num, cfg.explore_max_steps)

                turn_snapshot = TurnSnapshot(
                    turn_index=step_num,
                    actions_before_count=len(result.actions),
                    pages_before_count=len(result.pages),
                    browser_history_index=step_num,
                )

                tree = await capture_axtree(browser_session)
                selector_map = tree.get("selector_map") or {}
                page_info = PageInfo(
                    url=tree.get("url", ""),
                    title=tree.get("title", ""),
                    elements=list(selector_map.values()),
                )

                if not any(p.url == page_info.url for p in result.pages):
                    result.pages.append(page_info)

                element_tree_text = serialize_axtree(tree)
                selector_candidates_text = format_selector_candidates_section(selector_map)
                prompt_text = EXPLORE_PROMPT_TEMPLATE.format(
                    url=tree.get("url", ""),
                    title=tree.get("title", ""),
                    element_tree=element_tree_text,
                    selector_candidates=selector_candidates_text,
                    workflow_description=workflow_description,
                    completed_steps=completed_steps_text,
                )

                atom_inventory = build_atom_inventory_section(domain)
                if atom_inventory:
                    prompt_text = f"{prompt_text}\n\n{atom_inventory}"

                extend_section = ""
                if self._extend_context is not None:
                    cmds = self._extend_context.get("existing_commands", [])
                    domain_name = self._extend_context.get("domain", "")
                    lines = [f"\n\n## 已有命令（{domain_name}）— 请勿重复生成\n"]
                    for c in cmds:
                        args_text = (
                            "，".join(f"{a['name']}: {a['description']}" for a in c.get("args", []) if a.get("name"))
                            or "（无参数）"
                        )
                        lines.append(f"- **{c['name']}**: {c['description']} | 参数: {args_text}")
                    extend_section = "\n".join(lines)

                screenshot_data = tree.get("screenshot", b"")
                if cfg.vision_enabled and screenshot_data:
                    from cliany_site.browser.screenshot import (
                        annotate_screenshot_with_som,
                        enrich_selector_map_with_bounds,
                    )
                    from cliany_site.explorer.prompts import VISION_SUPPLEMENT_PROMPT
                    from cliany_site.explorer.vision import build_multimodal_message

                    enriched_map = await enrich_selector_map_with_bounds(
                        browser_session,
                        selector_map,
                    )
                    annotated_screenshot, _ref_to_label = annotate_screenshot_with_som(
                        screenshot_data,
                        enriched_map,
                        format=cfg.screenshot_format,
                        quality=cfg.screenshot_quality,
                        max_labels=cfg.vision_som_max_labels,
                    )

                    full_text = f"{SYSTEM_PROMPT}{extend_section}\n\n{prompt_text}\n\n{VISION_SUPPLEMENT_PROMPT}"
                    llm_input: Any = build_multimodal_message(
                        full_text,
                        annotated_screenshot or screenshot_data,
                        screenshot_format=cfg.screenshot_format,
                    )
                else:
                    llm_input = f"{SYSTEM_PROMPT}{extend_section}\n\n{prompt_text}"

                try:
                    logger.debug(
                        "步骤 %d: 调用 LLM (page=%s vision=%s)",
                        step_num + 1,
                        tree.get("url", ""),
                        bool(cfg.vision_enabled and screenshot_data),
                    )
                    reporter.on_explore_llm_start(step_num)
                    response = await _invoke_llm_with_retry(
                        llm,
                        llm_input,
                        max_attempts=cfg.llm_retry_max_attempts,
                        base_delay=cfg.llm_retry_base_delay,
                        backoff_factor=cfg.llm_retry_backoff_factor,
                    )
                    logger.debug("步骤 %d: LLM 响应已收到", step_num + 1)
                except AttributeError as e:
                    if "model_dump" in str(e):
                        raise RuntimeError(
                            "OpenAI 兼容接口返回格式异常；若使用代理，"
                            "请将 CLIANY_OPENAI_BASE_URL 配置为包含 /v1 的地址"
                            "（例如 https://sub2api.chinahrt.com/v1）"
                        ) from e
                    raise
                response_text = _to_text(response.content)
                parsed = _parse_llm_response(response_text)

                actions_data = _sanitize_actions_data(parsed.get("actions", []), tree.get("url", ""))
                reporter.on_explore_llm_done(step_num, len(actions_data))

                if interactive_ctrl is not None:
                    page_summary = f"{tree.get('title', '')} ({tree.get('url', '')})"
                    decision = await interactive_ctrl.prompt_action_confirmation(actions_data, page_summary)
                    from cliany_site.explorer.interactive import DecisionType

                    if decision.decision_type == DecisionType.SKIP:
                        step_elapsed = (time.monotonic() - step_start) * 1000
                        reporter.on_explore_step_done(step_num, 0, step_elapsed)
                        logger.info("步骤 %d 被用户跳过", step_num + 1)
                        continue
                    if decision.decision_type == DecisionType.MODIFY:
                        if decision.field and decision.field in ("value", "ref"):
                            for ad in actions_data:
                                if isinstance(ad, dict):
                                    ad[decision.field] = decision.new_value or ""
                    elif decision.decision_type == DecisionType.ROLLBACK:
                        rollback_success = await interactive_ctrl.handle_rollback(
                            turn_snapshot,
                            result,
                            browser_session,
                            recording_manager=recording_manager,
                            recording_manifest=recording_manifest,
                        )
                        if not rollback_success:
                            click.echo("⚠️ 已在第一步，无法继续回退", err=True)
                        reporter.on_explore_step_done(step_num, 0, 0)
                        continue

                for action_data in actions_data:
                    if not isinstance(action_data, dict):
                        continue
                    action_type = action_data.get("type", "unknown")
                    target_ref = str(action_data.get("ref", "") or "")
                    selector = selector_map.get(target_ref, {})
                    if not isinstance(selector, dict):
                        selector = {}

                    # reuse_atom 操作：atom_id 存入 target_ref，parameters 存入 target_attributes
                    if action_type == "reuse_atom":
                        atom_id = str(action_data.get("reuse_atom", "") or "")
                        params = action_data.get("parameters", {})
                        if not isinstance(params, dict):
                            params = {}
                        action = ActionStep(
                            action_type="reuse_atom",
                            page_url=tree.get("url", ""),
                            target_ref=atom_id,
                            target_url="",
                            value="",
                            description=action_data.get("description", ""),
                            target_name="",
                            target_role="",
                            target_attributes=params,
                        )
                    else:
                        action = ActionStep(
                            action_type=action_type,
                            page_url=tree.get("url", ""),
                            target_ref=target_ref,
                            target_url=action_data.get("url", ""),
                            value=action_data.get("value", ""),
                            description=action_data.get("description", ""),
                            target_name=str(selector.get("name", "") or ""),
                            target_role=str(selector.get("role", "") or ""),
                            target_attributes=dict(selector.get("attributes", {}) or {}),
                            selector=action_data.get("selector", "") if action_type == "extract" else "",
                            extract_mode=action_data.get("extract_mode", "text")
                            if action_type == "extract"
                            else "text",
                            fields_map=action_data.get("fields", {}) if action_type == "extract" else {},
                        )
                    result.actions.append(action)

                    description = action_data.get("description")
                    if isinstance(description, str) and description:
                        completed_steps.append(description)

                if completed_steps:
                    completed_steps_text = "\n".join(f"{i + 1}. {desc}" for i, desc in enumerate(completed_steps))

                _extraction_results: list = []
                await execute_action_steps(
                    browser_session, actions_data, continue_on_error=True, extraction_results=_extraction_results
                )
                if _extraction_results:
                    all_extraction_results.extend(_extraction_results)

                if recording_manager is not None and recording_manifest is not None:
                    try:
                        step_screenshot = await capture_screenshot(
                            browser_session,
                            format="png",
                            quality=cfg.screenshot_quality,
                            full_page=False,
                        )
                        step_axtree = await capture_axtree(browser_session)
                        step_record = StepRecord(
                            step_index=step_num,
                            action_data={
                                "actions": actions_data,
                                "done": bool(parsed.get("done", False)),
                                "next_url": str(parsed.get("next_url", "") or ""),
                            },
                            llm_response_raw=response_text,
                            timestamp=datetime.now(UTC).isoformat(),
                        )
                        recording_manager.save_step(
                            manifest=recording_manifest,
                            step_record=step_record,
                            screenshot_bytes=step_screenshot or None,
                            axtree_json=step_axtree,
                        )
                    except Exception as e:
                        logger.warning("步骤录像保存失败，将继续探索: %s", e)

                step_elapsed = (time.monotonic() - step_start) * 1000
                reporter.on_explore_step_done(step_num, len(actions_data), step_elapsed)
                logger.info(
                    "步骤 %d 完成: %d 个动作, 耗时 %.0fms",
                    step_num + 1,
                    len(actions_data),
                    step_elapsed,
                )

                if parsed.get("done", False):
                    if interactive_ctrl is not None:
                        ask_continue = getattr(interactive_ctrl, "ask_continue_after_done", None)
                        if callable(ask_continue):
                            maybe_keep_going = ask_continue()
                            if asyncio.iscoroutine(maybe_keep_going):
                                keep_going = await maybe_keep_going
                            else:
                                keep_going = bool(maybe_keep_going)
                            if keep_going:
                                logger.info("步骤 %d: 用户选择继续探索", step_num + 1)
                                continue

                    logger.info(
                        "探索完成: 共 %d 步, %d 个动作, %d 个命令",
                        step_num + 1,
                        len(result.actions),
                        len(parsed.get("commands", [])),
                    )
                    final_step_count = step_num + 1
                    commands_data = parsed.get("commands", [])
                    if not isinstance(commands_data, list):
                        commands_data = []

                    for cmd_data in commands_data:
                        if not isinstance(cmd_data, dict):
                            continue
                        args = cmd_data.get("args", [])
                        if not isinstance(args, list):
                            args = []

                        raw_action_steps = cmd_data.get("action_steps")
                        if isinstance(raw_action_steps, list):
                            action_steps = [
                                idx
                                for idx in raw_action_steps
                                if isinstance(idx, int) and 0 <= idx < len(result.actions)
                            ]
                        else:
                            action_steps = []  # will be fixed in validation below

                        cmd = CommandSuggestion(
                            name=cmd_data.get("name", f"command-{len(result.commands) + 1}"),
                            description=cmd_data.get("description", ""),
                            args=args,
                            action_steps=action_steps,
                        )
                        result.commands.append(cmd)

                    for cmd in result.commands:
                        if not cmd.args:
                            cmd.args = _infer_params_from_actions(result.actions, workflow_description)
                        if cmd.name in _GENERIC_COMMAND_NAMES:
                            better = _infer_command_name_from_description(cmd.description or workflow_description)
                            if better:
                                cmd.name = better

                    all_action_indices = set(range(len(result.actions)))
                    assigned_indices: set[int] = set()
                    for cmd in result.commands:
                        assigned_indices.update(cmd.action_steps)

                    if assigned_indices != all_action_indices:
                        # LLM didn't provide valid partitioning — fall back
                        if len(result.commands) == 1:
                            result.commands[0].action_steps = list(range(len(result.actions)))
                        else:
                            total = len(result.actions)
                            n_cmds = len(result.commands)
                            per_cmd = total // n_cmds if n_cmds else total
                            start = 0
                            for i, cmd in enumerate(result.commands):
                                end = start + per_cmd if i < n_cmds - 1 else total
                                cmd.action_steps = list(range(start, end))
                                start = end

                    _ca = parsed.get("canonical_actions", [])
                    result.canonical_actions = [a for a in _ca if isinstance(a, dict)]
                    _sp = parsed.get("selector_pool", [])
                    result.selector_pool = [s for s in _sp if isinstance(s, dict)]
                    result.smoke = [
                        {"action": "navigate", "url": url},
                        {"action": "state"},
                    ]

                    break

                next_url = normalize_navigation_url(parsed.get("next_url", ""), tree.get("url", ""))
                if next_url and next_url != tree.get("url", ""):
                    with contextlib.suppress(OSError, RuntimeError, TimeoutError):
                        await browser_session.navigate_to(next_url, new_tab=False)

            if not result.commands and result.actions:
                inferred_args = _infer_params_from_actions(result.actions, workflow_description)
                fallback_name = _infer_command_name_from_description(workflow_description) or "run-workflow"
                result.commands.append(
                    CommandSuggestion(
                        name=fallback_name,
                        description=workflow_description,
                        args=inferred_args,
                        action_steps=list(range(len(result.actions))),
                    )
                )

            saved_path = save_extract_markdown(
                extraction_results=all_extraction_results,
                domain=domain,
                workflow_description=workflow_description,
            )
            if saved_path:
                click.echo(f"📄 提取结果已保存: {saved_path}", err=True)
            explore_completed = True
        except KeyboardInterrupt:
            n_commands = len(result.commands)
            try:
                code = AdapterGenerator().generate(result, domain)
                save_adapter(domain, code, explore_result=result)
            except Exception as gen_err:
                logger.warning("Ctrl-C 中断后保存部分适配器失败: %s", gen_err)
            if recording_manager is not None and recording_manifest is not None:
                try:
                    recording_manager.finalize(recording_manifest, completed=False)
                    _recording_finalized = True
                except Exception as finalize_err:
                    logger.warning("录像截断写入失败: %s", finalize_err)
            click.echo(f"探索被 Ctrl-C 中断，已保存 {n_commands} 个命令和录像", err=True)
            raise
        except Exception as e:
            logger.debug("探索异常，准备以失败态结束录像: %s", e)
            if recording_manager is not None and recording_manifest is not None:
                try:
                    recording_manager.finalize(recording_manifest, completed=False)
                    _recording_finalized = True
                except Exception as finalize_error:
                    logger.warning("录像结束写入失败(失败态): %s", finalize_error)
            raise
        finally:
            if (
                explore_completed
                and not _recording_finalized
                and recording_manager is not None
                and recording_manifest is not None
            ):
                try:
                    recording_manager.finalize(recording_manifest, completed=True)
                except Exception as finalize_error:
                    logger.warning("录像结束写入失败(完成态): %s", finalize_error)
            if self._cdp is not None:
                await self._cdp.disconnect()

        total_elapsed = (time.monotonic() - explore_start) * 1000
        reporter.on_explore_done(
            total_steps=final_step_count,
            total_actions=len(result.actions),
            total_commands=len(result.commands),
            elapsed_ms=total_elapsed,
        )
        logger.info(
            "探索结束: %d 个动作, %d 个命令, 总耗时 %.0fms",
            len(result.actions),
            len(result.commands),
            total_elapsed,
        )
        return result
