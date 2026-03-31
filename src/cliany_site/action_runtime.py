import asyncio
import contextlib
import copy
import logging
import re
import time
from datetime import UTC
from typing import Any, cast
from urllib.parse import urljoin, urlparse

from cliany_site.browser.axtree import capture_axtree, serialize_axtree
from cliany_site.config import get_config
from cliany_site.errors import ClanySiteError
from cliany_site.extract import build_extract_js
from cliany_site.progress import NullProgressReporter, ProgressReporter

logger = logging.getLogger(__name__)


class ActionExecutionError(ClanySiteError):
    """操作执行失败时的结构化异常"""

    def __init__(
        self,
        error_type: str,
        action_index: int,
        action: dict[str, Any],
        message: str,
        suggestion: str = "",
    ):
        self.error_type = error_type
        self.action_index = action_index
        self.action = action
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type,
            "action_index": self.action_index,
            "action": self.action,
            "message": self.message,
            "suggestion": self.suggestion,
        }


def _get_post_navigate_delay() -> float:
    return get_config().post_navigate_delay


def _get_post_click_nav_delay() -> float:
    return get_config().post_click_nav_delay


def _get_new_tab_settle_delay() -> float:
    return get_config().new_tab_settle_delay


def _get_resolve_retry_delay() -> float:
    return get_config().resolve_retry_delay


def _get_resolve_max_retries() -> int:
    return get_config().resolve_max_retries


def _get_adaptive_repair_max_attempts() -> int:
    return get_config().adaptive_repair_max_attempts


def _adaptive_repair_enabled() -> bool:
    return get_config().adaptive_repair_enabled


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _parse_ref_to_index(ref: str) -> int | None:
    match = re.search(r"(\d+)", ref or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def normalize_navigation_url(candidate: Any, current_url: str) -> str:
    if not isinstance(candidate, str):
        return ""

    raw = candidate.strip()
    wrapper_pairs = {
        '"': '"',
        "'": "'",
        "“": "”",
        "‘": "’",
        "(": ")",
        "（": "）",
        "[": "]",
        "{": "}",
        "<": ">",
    }
    closing = wrapper_pairs.get(raw[:1])
    if closing and raw.endswith(closing):
        raw = raw[1:-1].strip()
    raw = raw.rstrip("，。；：！？、,;:!?")
    if not raw or any(char.isspace() for char in raw):
        return ""

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return raw

    if current_url and not parsed.scheme and not parsed.netloc and raw.startswith(("/", "./", "../", "?", "#")):
        absolute_url = urljoin(current_url, raw)
        absolute = urlparse(absolute_url)
        if absolute.scheme in {"http", "https"} and absolute.netloc:
            return absolute_url

    return ""


def _normalize_attr_value(value: Any, current_url: str) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    url_value = normalize_navigation_url(str(value), current_url)
    return _normalize_text(url_value or value)


def substitute_parameters(actions_data: list[dict[str, Any]], params: dict[str, Any]) -> list[dict[str, Any]]:
    substituted = copy.deepcopy(actions_data)
    if not isinstance(params, dict) or not params:
        return substituted

    pattern = re.compile(r"\{\{(\w+)\}\}")

    for action_data in substituted:
        if not isinstance(action_data, dict):
            continue

        for field_name in ("value", "url", "description", "target_name", "selector"):
            field_value = action_data.get(field_name)
            if not isinstance(field_value, str):
                continue

            action_data[field_name] = pattern.sub(
                lambda match: str(params.get(match.group(1), match.group(0))),
                field_value,
            )

    return substituted


def _score_candidate(
    action_data: dict[str, Any],
    candidate: dict[str, Any],
    current_url: str,
) -> int:
    score = 0

    target_name = _normalize_text(action_data.get("target_name", ""))
    candidate_name = _normalize_text(candidate.get("name", ""))
    if target_name and candidate_name:
        if candidate_name == target_name:
            score += 40
        elif target_name in candidate_name or candidate_name in target_name:
            score += 20

    target_role = _normalize_text(action_data.get("target_role", ""))
    candidate_role = _normalize_text(candidate.get("role", ""))
    if target_role and candidate_role and target_role == candidate_role:
        score += 15

    target_frame_id = action_data.get("target_frame_id", "")
    candidate_frame_id = candidate.get("frame_id", "")
    if target_frame_id and candidate_frame_id and str(target_frame_id) == str(candidate_frame_id):
        score += 10

    target_shadow = action_data.get("target_shadow_root_type", "")
    candidate_shadow = candidate.get("shadow_root_type", "")
    if target_shadow and candidate_shadow and str(target_shadow) == str(candidate_shadow):
        score += 5

    target_attributes = action_data.get("target_attributes", {})
    candidate_attributes = candidate.get("attributes", {})
    if isinstance(target_attributes, dict) and isinstance(candidate_attributes, dict):
        for key, weight in {
            "id": 30,
            "name": 20,
            "aria-label": 20,
            "placeholder": 18,
            "href": 18,
            "title": 12,
            "type": 12,
            "role": 10,
        }.items():
            target_value = _normalize_attr_value(target_attributes.get(key), current_url)
            candidate_value = _normalize_attr_value(candidate_attributes.get(key), current_url)
            if target_value and candidate_value and target_value == candidate_value:
                score += weight

        target_class = _normalize_text(target_attributes.get("class", ""))
        candidate_class = _normalize_text(candidate_attributes.get("class", ""))
        if target_class and candidate_class:
            overlap = set(target_class.split()) & set(candidate_class.split())
            score += min(len(overlap) * 3, 9)

    return score


def _action_has_href(action_data: dict[str, Any]) -> bool:
    attrs = action_data.get("target_attributes", {})
    return bool(isinstance(attrs, dict) and attrs.get("href"))


def _action_opens_new_tab(action_data: dict[str, Any]) -> bool:
    attrs = action_data.get("target_attributes", {})
    return isinstance(attrs, dict) and str(attrs.get("target", "")).strip() == "_blank"


def _extract_repair_selector_refs(parsed_response: Any) -> list[str]:
    if not isinstance(parsed_response, dict):
        return []

    selectors = parsed_response.get("selectors", [])
    if not isinstance(selectors, list):
        return []

    normalized: list[str] = []
    for selector in selectors:
        normalized_ref = str(selector or "").strip()
        if normalized_ref and normalized_ref not in normalized:
            normalized.append(normalized_ref)
    return normalized


async def _attempt_adaptive_repair(browser_session: Any, action_data: dict[str, Any]) -> Any | None:
    import importlib

    from cliany_site.repair_prompts import REPAIR_PROMPT_TEMPLATE

    try:
        engine_module = importlib.import_module("cliany_site.explorer.engine")
    except (ImportError, ModuleNotFoundError):
        return None

    get_replay_llm = getattr(engine_module, "_get_replay_llm", None)
    if not callable(get_replay_llm):
        get_replay_llm = getattr(engine_module, "_get_llm", None)
    if not callable(get_replay_llm):
        return None

    llm = None
    for kwargs in ({"role": "replay"}, {}, {"role": "explore"}):
        try:
            llm = get_replay_llm(**kwargs) if kwargs else get_replay_llm()
            break
        except TypeError:
            continue
        except (OSError, ValueError, ImportError) as exc:
            logger.debug("获取 replay LLM 失败: %s", exc)
            return None

    if llm is None:
        return None

    parse_llm_response = getattr(engine_module, "_parse_llm_response", None)
    if not callable(parse_llm_response):
        return None
    to_text = getattr(engine_module, "_to_text", None)

    repair_attempts = action_data.get("repair_attempts")
    if not isinstance(repair_attempts, list):
        repair_attempts = []
        action_data["repair_attempts"] = repair_attempts

    original_ref = str(action_data.get("ref", "") or action_data.get("target_ref", ""))
    attempted_refs: list[str] = [original_ref] if original_ref else []

    for llm_attempt in range(_get_adaptive_repair_max_attempts()):
        tree = await capture_axtree(browser_session)
        selector_map = tree.get("selector_map", {})

        prompt_text = REPAIR_PROMPT_TEMPLATE.format(
            current_url=tree.get("url", ""),
            page_title=tree.get("title", ""),
            action_type=str(action_data.get("type", "")),
            action_description=str(action_data.get("description", "")),
            original_ref=original_ref,
            target_name=str(action_data.get("target_name", "")),
            target_role=str(action_data.get("target_role", "")),
            target_attributes=action_data.get("target_attributes", {}),
            attempted_refs=attempted_refs,
            element_tree=serialize_axtree(tree),
        )

        attempt_record: dict[str, Any] = {
            "strategy": "adaptive_repair",
            "attempt": llm_attempt + 1,
            "attempted_refs": list(attempted_refs),
        }

        try:
            ainvoke = getattr(llm, "ainvoke", None)
            if callable(ainvoke):
                maybe_async_result = ainvoke(prompt_text)
                if asyncio.iscoroutine(maybe_async_result):
                    response = await cast(Any, maybe_async_result)
                else:
                    response = maybe_async_result
            else:
                invoke = getattr(llm, "invoke", None)
                if not callable(invoke):
                    raise TypeError("LLM 对象缺少 invoke/ainvoke 接口")
                response = invoke(prompt_text)
            response_content = getattr(response, "content", response)
            response_text = to_text(response_content) if callable(to_text) else str(response_content)
            parsed = parse_llm_response(response_text)
        except (TypeError, ValueError, RuntimeError, OSError) as exc:
            logger.debug("自适应修复 LLM 调用失败 (attempt=%d): %s", llm_attempt + 1, exc)
            attempt_record["success"] = False
            attempt_record["error"] = str(exc)
            repair_attempts.append(attempt_record)
            continue

        selector_refs = _extract_repair_selector_refs(parsed)
        attempt_record["selector_refs"] = selector_refs

        for candidate_ref in selector_refs:
            if candidate_ref not in attempted_refs:
                attempted_refs.append(candidate_ref)

            candidate_index = _parse_ref_to_index(candidate_ref)
            if candidate_index is None:
                continue

            if not isinstance(selector_map.get(str(candidate_index)), dict):
                continue

            try:
                node = await browser_session.get_element_by_index(candidate_index)
            except (IndexError, KeyError, RuntimeError, OSError) as exc:
                logger.debug("自适应修复: 元素 %s 定位失败: %s", candidate_index, exc)
                continue

            attempt_record["success"] = True
            attempt_record["resolved_ref"] = str(candidate_index)
            repair_attempts.append(attempt_record)
            return node

        attempt_record["success"] = False
        repair_attempts.append(attempt_record)

    return None


async def _switch_to_newest_tab(browser_session: Any) -> None:
    import importlib

    events_module = importlib.import_module("browser_use.browser.events")
    SwitchTabEvent = events_module.SwitchTabEvent

    event = browser_session.event_bus.dispatch(SwitchTabEvent(target_id=None))
    await event
    await event.event_result(raise_if_any=False, raise_if_none=False)


async def _handle_post_click_navigation(
    browser_session: Any,
    action_data: dict[str, Any],
) -> None:
    if _action_opens_new_tab(action_data):
        await asyncio.sleep(0.5)
        await _switch_to_newest_tab(browser_session)
        await asyncio.sleep(_get_new_tab_settle_delay())
    elif _action_has_href(action_data):
        await asyncio.sleep(_get_post_click_nav_delay())


async def _resolve_action_node(browser_session: Any, action_data: dict[str, Any]) -> Any | None:
    for attempt in range(_get_resolve_max_retries() + 1):
        tree = await capture_axtree(browser_session)
        selector_map = tree.get("selector_map", {})
        current_url = tree.get("url", "")

        ref_value = str(action_data.get("ref", "") or action_data.get("target_ref", ""))
        direct_index = _parse_ref_to_index(ref_value)
        if direct_index is not None:
            direct_candidate = selector_map.get(str(direct_index))
            if isinstance(direct_candidate, dict):
                direct_score = _score_candidate(action_data, direct_candidate, current_url)
                if direct_score > 0 or not any(
                    action_data.get(key) for key in ("target_name", "target_role", "target_attributes")
                ):
                    return await browser_session.get_element_by_index(direct_index)

        best_index: int | None = None
        best_score = 0
        for ref, candidate in selector_map.items():
            if not isinstance(candidate, dict):
                continue
            score = _score_candidate(action_data, candidate, current_url)
            if score > best_score:
                candidate_index = _parse_ref_to_index(str(ref))
                if candidate_index is not None:
                    best_index = candidate_index
                    best_score = score

        if best_index is not None and best_score > 0:
            return await browser_session.get_element_by_index(best_index)

        if attempt < _get_resolve_max_retries():
            await asyncio.sleep(_get_resolve_retry_delay())

    if _adaptive_repair_enabled():
        repaired = await _attempt_adaptive_repair(browser_session, action_data)
        if repaired is not None:
            return repaired

    return None


async def execute_action_steps(
    browser_session: Any,
    actions_data: list[dict[str, Any]],
    continue_on_error: bool = False,
    params: dict[str, Any] | None = None,
    domain: str = "",
    command_name: str = "",
    progress: ProgressReporter | None = None,
    start_index: int = 0,
    dry_run: bool = False,
    extraction_results: list | None = None,
) -> None:
    import importlib
    from datetime import datetime

    from cliany_site.checkpoint import clear_checkpoint, save_checkpoint
    from cliany_site.report import ActionStepResult, ExecutionReport, save_execution_log, save_report

    events_module = importlib.import_module("browser_use.browser.events")
    ClickElementEvent = events_module.ClickElementEvent
    NavigateToUrlEvent = events_module.NavigateToUrlEvent
    SelectDropdownOptionEvent = events_module.SelectDropdownOptionEvent
    SendKeysEvent = events_module.SendKeysEvent
    TypeTextEvent = events_module.TypeTextEvent

    effective_actions = substitute_parameters(actions_data, params) if params is not None else actions_data
    reporter: ProgressReporter = progress or NullProgressReporter()

    mode_label = "[dry-run] " if dry_run else ""
    logger.info(
        "%s开始执行: %d 个动作 domain=%s command=%s start_index=%d",
        mode_label,
        len(effective_actions),
        domain or "(unknown)",
        command_name or "(default)",
        start_index,
    )

    resolved_domain = domain
    if not resolved_domain:
        for _a in effective_actions:
            if isinstance(_a, dict) and str(_a.get("type", "")).lower() == "navigate":
                _url = _a.get("url", "")
                if _url:
                    try:
                        resolved_domain = urlparse(_url).netloc or _url
                    except (ValueError, AttributeError):
                        resolved_domain = _url
                    break

    started_at = datetime.now(UTC).isoformat()
    step_results: list[ActionStepResult] = []
    completed_indices: list[int] = []
    execute_start = time.monotonic()
    reporter.on_execute_start(len(effective_actions), resolved_domain, command_name)

    try:
        for idx, action_data in enumerate(effective_actions):
            if not isinstance(action_data, dict):
                continue

            action_type = str(action_data.get("type", "")).lower()
            if action_type not in ("click", "type", "select", "navigate", "submit", "extract"):
                continue

            if idx < start_index:
                logger.debug("跳过已完成步骤 %d (start_index=%d)", idx, start_index)
                completed_indices.append(idx)
                continue

            step_start = time.monotonic()
            step_page_url = ""
            logger.debug(
                "%s步骤 %d/%d: type=%s desc=%s",
                mode_label,
                idx + 1,
                len(effective_actions),
                action_type,
                action_data.get("description", ""),
            )
            reporter.on_execute_step_start(
                idx, len(effective_actions), action_type, str(action_data.get("description", action_type))
            )

            try:
                try:
                    step_page_url = await browser_session.get_current_page_url()
                except Exception:
                    step_page_url = ""

                if dry_run:
                    if action_type == "navigate":
                        current_url = step_page_url
                        nav_url = normalize_navigation_url(action_data.get("url", ""), current_url)
                        if not nav_url:
                            raise ActionExecutionError(
                                error_type="invalid_url",
                                action_index=idx,
                                action=action_data,
                                message=f"[dry-run] 无效导航 URL: {action_data.get('url', '')}",
                                suggestion="URL 可能已变更，建议重新 explore",
                            )
                        logger.debug("[dry-run] navigate → %s (验证通过)", nav_url)
                    elif action_type == "extract":
                        logger.debug("[dry-run] extract 步骤 %d 跳过（不验证选择器）", idx)
                    else:
                        node = await _resolve_action_node(browser_session, action_data)
                        if node is None and action_type != "submit":
                            raise ActionExecutionError(
                                error_type="element_not_found",
                                action_index=idx,
                                action=action_data,
                                message=f"[dry-run] 未找到目标元素: {action_data.get('description', action_type)}",
                                suggestion="目标元素可能已更名或移除，建议重新 explore",
                            )
                        logger.debug("[dry-run] %s → 元素已定位 (验证通过)", action_type)

                elif action_type == "navigate":
                    current_url = step_page_url
                    nav_url = normalize_navigation_url(action_data.get("url", ""), current_url)
                    if not nav_url:
                        raise ActionExecutionError(
                            error_type="invalid_url",
                            action_index=idx,
                            action=action_data,
                            message=f"无效导航 URL: {action_data.get('url', '')}",
                            suggestion="URL 可能已变更，建议重新 explore",
                        )
                    event = browser_session.event_bus.dispatch(
                        NavigateToUrlEvent(
                            url=nav_url,
                            wait_until="load",
                            new_tab=False,
                        )
                    )
                    await event
                    await event.event_result(raise_if_any=not continue_on_error, raise_if_none=False)
                    await asyncio.sleep(_get_post_navigate_delay())

                elif action_type == "submit":
                    submit_node = await _resolve_action_node(browser_session, action_data)
                    if submit_node is not None:
                        event = browser_session.event_bus.dispatch(ClickElementEvent(node=submit_node))
                    else:
                        event = browser_session.event_bus.dispatch(SendKeysEvent(keys="Enter"))
                    await event
                    await event.event_result(raise_if_any=not continue_on_error, raise_if_none=False)
                    if _action_has_href(action_data) or _action_opens_new_tab(action_data):
                        await _handle_post_click_navigation(browser_session, action_data)

                elif action_type == "extract":
                    await asyncio.sleep(1.5)

                    selector = str(action_data.get("selector", "")).strip()
                    extract_mode = str(action_data.get("extract_mode", "text")).strip()
                    fields = action_data.get("fields", {}) or {}
                    description = str(action_data.get("description", ""))

                    if not selector:
                        logger.warning("extract 动作缺少 selector，跳过")
                    else:
                        try:
                            js_expr = build_extract_js(selector, extract_mode, fields if fields else None)
                            page = await browser_session.get_current_page()
                            if page is None:
                                logger.warning("extract 执行失败 (selector=%s): 无法获取当前页面", selector)
                                raw_result = None
                            else:
                                raw_result = await page.evaluate(js_expr)
                        except Exception as exc:
                            logger.warning("extract 执行失败 (selector=%s): %s", selector, exc)
                            raw_result = None

                        if extraction_results is not None:
                            if raw_result is None:
                                if extract_mode == "text":
                                    data = {"text": ""}
                                elif extract_mode == "attribute":
                                    data = {}
                                else:
                                    data = []
                            else:
                                data = raw_result

                            extraction_results.append(
                                {
                                    "step_index": idx,
                                    "extract_mode": extract_mode,
                                    "description": description,
                                    "data": data,
                                }
                            )

                else:
                    node = await _resolve_action_node(browser_session, action_data)
                    if node is None:
                        raise ActionExecutionError(
                            error_type="element_not_found",
                            action_index=idx,
                            action=action_data,
                            message=f"未找到目标元素: {action_data.get('description', action_type)}",
                            suggestion="目标元素可能已更名或移除，建议重新 explore",
                        )

                    if action_type == "click":
                        event = browser_session.event_bus.dispatch(ClickElementEvent(node=node))
                        await event
                        await event.event_result(raise_if_any=not continue_on_error, raise_if_none=False)
                        await _handle_post_click_navigation(browser_session, action_data)
                    elif action_type == "type":
                        value = action_data.get("value", "")
                        if isinstance(value, str):
                            event = browser_session.event_bus.dispatch(TypeTextEvent(node=node, text=value, clear=True))
                            await event
                            await event.event_result(raise_if_any=not continue_on_error, raise_if_none=False)
                    elif action_type == "select":
                        value = action_data.get("value", "")
                        if isinstance(value, str) and value:
                            event = browser_session.event_bus.dispatch(SelectDropdownOptionEvent(node=node, text=value))
                            await event
                            await event.event_result(raise_if_any=not continue_on_error, raise_if_none=False)

            except Exception as exc:
                logger.warning("%s步骤 %d (%s) 执行失败: %s", mode_label, idx, action_type, exc)
                step_elapsed_err = (time.monotonic() - step_start) * 1000
                step_results.append(
                    ActionStepResult(
                        step_index=idx,
                        action_type=action_type,
                        description=str(action_data.get("description", action_type)),
                        success=False,
                        error_message=str(exc),
                        timestamp=datetime.now(UTC).isoformat(),
                        page_url=step_page_url,
                        elapsed_ms=step_elapsed_err,
                    )
                )
                reporter.on_execute_step_done(idx, len(effective_actions), False, step_elapsed_err, str(exc))

                if not continue_on_error and not dry_run:
                    if resolved_domain and command_name:
                        try:
                            save_checkpoint(resolved_domain, command_name, actions_data, completed_indices, params)
                            logger.info("断点已保存，可使用 --resume 继续执行")
                        except (OSError, ValueError, TypeError) as ckpt_exc:
                            logger.debug("保存断点失败: %s", ckpt_exc)

                    if isinstance(exc, ActionExecutionError):
                        raise
                    raise ActionExecutionError(
                        error_type="execution_error",
                        action_index=idx,
                        action=action_data,
                        message=str(exc),
                        suggestion="操作执行异常，建议检查页面状态或重新 explore",
                    ) from exc
                continue

            step_elapsed = (time.monotonic() - step_start) * 1000
            step_results.append(
                ActionStepResult(
                    step_index=idx,
                    action_type=action_type,
                    description=str(action_data.get("description", action_type)),
                    success=True,
                    error_message=None,
                    timestamp=datetime.now(UTC).isoformat(),
                    page_url=step_page_url,
                    elapsed_ms=step_elapsed,
                )
            )
            completed_indices.append(idx)
            reporter.on_execute_step_done(idx, len(effective_actions), True, step_elapsed)
            logger.debug("%s步骤 %d 完成: 耗时 %.0fms", mode_label, idx + 1, step_elapsed)

    finally:
        total_execute_elapsed = (time.monotonic() - execute_start) * 1000
        succeeded = sum(1 for s in step_results if s.success)
        failed = sum(1 for s in step_results if not s.success)
        reporter.on_execute_done(succeeded, failed, len(step_results), total_execute_elapsed)

        if resolved_domain:
            finished_at = datetime.now(UTC).isoformat()
            logger.info(
                "%s执行完成: 成功=%d 失败=%d 总计=%d domain=%s",
                mode_label,
                succeeded,
                failed,
                len(step_results),
                resolved_domain,
            )
            report = ExecutionReport(
                adapter_domain=resolved_domain,
                command_name=command_name,
                started_at=started_at,
                finished_at=finished_at,
                total_steps=len(step_results),
                succeeded_steps=succeeded,
                failed_steps=failed,
                repaired_steps=0,
                step_results=step_results,
            )
            try:
                save_report(report, resolved_domain)
            except (OSError, ValueError, TypeError) as exc:
                logger.debug("保存执行报告失败: %s", exc)
            try:
                save_execution_log(report, resolved_domain)
            except (OSError, ValueError, TypeError) as exc:
                logger.debug("保存执行日志失败: %s", exc)

            if failed == 0 and resolved_domain and command_name:
                with contextlib.suppress(OSError, ValueError, TypeError):
                    clear_checkpoint(resolved_domain, command_name)
