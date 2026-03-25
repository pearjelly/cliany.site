import asyncio
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from cliany_site.browser.axtree import capture_axtree

# 导航后等待页面动态内容渲染的时间（秒）
_POST_NAVIGATE_DELAY = 1.5
# 元素定位失败后重试前的等待时间（秒）
_RESOLVE_RETRY_DELAY = 1.0
# 元素定位最大重试次数
_RESOLVE_MAX_RETRIES = 2


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

    if (
        current_url
        and not parsed.scheme
        and not parsed.netloc
        and raw.startswith(("/", "./", "../", "?", "#"))
    ):
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
            target_value = _normalize_attr_value(
                target_attributes.get(key), current_url
            )
            candidate_value = _normalize_attr_value(
                candidate_attributes.get(key), current_url
            )
            if target_value and candidate_value and target_value == candidate_value:
                score += weight

        target_class = _normalize_text(target_attributes.get("class", ""))
        candidate_class = _normalize_text(candidate_attributes.get("class", ""))
        if target_class and candidate_class:
            overlap = set(target_class.split()) & set(candidate_class.split())
            score += min(len(overlap) * 3, 9)

    return score


async def _resolve_action_node(
    browser_session: Any, action_data: dict[str, Any]
) -> Any | None:
    for attempt in range(_RESOLVE_MAX_RETRIES + 1):
        tree = await capture_axtree(browser_session)
        selector_map = tree.get("selector_map", {})
        current_url = tree.get("url", "")

        ref_value = str(action_data.get("ref", "") or action_data.get("target_ref", ""))
        direct_index = _parse_ref_to_index(ref_value)
        if direct_index is not None:
            direct_candidate = selector_map.get(str(direct_index))
            if isinstance(direct_candidate, dict):
                direct_score = _score_candidate(
                    action_data, direct_candidate, current_url
                )
                if direct_score > 0 or not any(
                    action_data.get(key)
                    for key in ("target_name", "target_role", "target_attributes")
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

        if attempt < _RESOLVE_MAX_RETRIES:
            await asyncio.sleep(_RESOLVE_RETRY_DELAY)

    return None


async def execute_action_steps(
    browser_session: Any,
    actions_data: list[dict[str, Any]],
    continue_on_error: bool = False,
) -> None:
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
            action_type = str(action_data.get("type", "")).lower()

            if action_type not in ("click", "type", "select", "navigate", "submit"):
                continue

            if action_type == "navigate":
                current_url = await browser_session.get_current_page_url()
                nav_url = normalize_navigation_url(
                    action_data.get("url", ""), current_url
                )
                if not nav_url:
                    raise RuntimeError(f"无效导航 URL: {action_data.get('url', '')}")
                event = browser_session.event_bus.dispatch(
                    NavigateToUrlEvent(
                        url=nav_url,
                        wait_until="load",
                        new_tab=False,
                    )
                )
                await event
                await event.event_result(
                    raise_if_any=not continue_on_error, raise_if_none=False
                )
                await asyncio.sleep(_POST_NAVIGATE_DELAY)
                continue

            if action_type == "submit":
                event = browser_session.event_bus.dispatch(SendKeysEvent(keys="Enter"))
                await event
                await event.event_result(
                    raise_if_any=not continue_on_error, raise_if_none=False
                )
                continue

            node = await _resolve_action_node(browser_session, action_data)
            if node is None:
                raise RuntimeError(
                    f"未找到目标元素: {action_data.get('description', action_type)}"
                )

            if action_type == "click":
                event = browser_session.event_bus.dispatch(ClickElementEvent(node=node))
                await event
                await event.event_result(
                    raise_if_any=not continue_on_error, raise_if_none=False
                )
            elif action_type == "type":
                value = action_data.get("value", "")
                if isinstance(value, str):
                    event = browser_session.event_bus.dispatch(
                        TypeTextEvent(node=node, text=value, clear=True)
                    )
                    await event
                    await event.event_result(
                        raise_if_any=not continue_on_error, raise_if_none=False
                    )
            elif action_type == "select":
                value = action_data.get("value", "")
                if isinstance(value, str) and value:
                    event = browser_session.event_bus.dispatch(
                        SelectDropdownOptionEvent(node=node, text=value)
                    )
                    await event
                    await event.event_result(
                        raise_if_any=not continue_on_error, raise_if_none=False
                    )
        except Exception:
            if not continue_on_error:
                raise
