"""
AXTree 捕获与序列化 — 包装 browser-use DomService API

DomService 需要 BrowserSession（非 Page）；get_serialized_dom_tree() 返回
tuple[SerializedDOMState, EnhancedDOMTreeNode, dict]；llm_representation() 生成
带 @ref 标记的可交互元素文本。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cliany_site.browser.selector import enrich_selector_map

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

MAX_CHARS = 20_000


def _count_nested_contexts(selector_map_raw: dict[int, Any]) -> dict[str, int]:
    frame_ids: set[str] = set()
    shadow_count = 0

    for element in selector_map_raw.values():
        frame_id = getattr(element, "frame_id", None)
        if frame_id:
            frame_ids.add(str(frame_id))

        shadow_root_type = getattr(element, "shadow_root_type", None)
        if shadow_root_type:
            shadow_count += 1

    return {
        "iframe_count": max(len(frame_ids) - 1, 0),
        "shadow_root_count": shadow_count,
        "unique_frame_ids": len(frame_ids),
    }


async def capture_axtree(browser_session: Any) -> dict:
    from browser_use.dom.service import DomService

    from cliany_site.config import get_config

    cfg = get_config()
    dom_service = DomService(
        browser_session,
        cross_origin_iframes=cfg.cross_origin_iframes,
        max_iframes=cfg.max_iframes,
        max_iframe_depth=cfg.max_iframe_depth,
    )
    serialized, _enhanced_tree, _timing = await dom_service.get_serialized_dom_tree()

    if hasattr(serialized, "selector_map") and serialized.selector_map:
        browser_session.update_cached_selector_map(serialized.selector_map)

    element_tree_text = serialized.llm_representation()

    selector_map: dict[str, dict] = {}
    nested_stats: dict[str, int] = {"iframe_count": 0, "shadow_root_count": 0, "unique_frame_ids": 0}

    if hasattr(serialized, "selector_map") and serialized.selector_map:
        nested_stats = _count_nested_contexts(serialized.selector_map)

        for ref_id, element in serialized.selector_map.items():
            try:
                role = element.tag_name if hasattr(element, "tag_name") else "unknown"
                ax_name = ""
                if hasattr(element, "ax_node") and element.ax_node is not None:
                    ax_name = getattr(element.ax_node, "name", "") or ""
                if not ax_name:
                    ax_name = element.node_value if hasattr(element, "node_value") else ""

                frame_id = getattr(element, "frame_id", None)
                target_id = getattr(element, "target_id", None)
                shadow_root_type = getattr(element, "shadow_root_type", None)

                entry: dict[str, Any] = {
                    "ref": str(ref_id),
                    "role": role,
                    "name": ax_name,
                    "attributes": dict(getattr(element, "attributes", {}) or {}),
                }
                if frame_id:
                    entry["frame_id"] = str(frame_id)
                if target_id:
                    entry["target_id"] = str(target_id)
                if shadow_root_type:
                    entry["shadow_root_type"] = str(shadow_root_type)

                selector_map[str(ref_id)] = entry
            except (AttributeError, TypeError, KeyError):
                selector_map[str(ref_id)] = {"ref": str(ref_id)}

    selector_map = enrich_selector_map(selector_map)

    if nested_stats["iframe_count"] > 0 or nested_stats["shadow_root_count"] > 0:
        logger.info(
            "AXTree 嵌套上下文: iframe=%d shadow_root=%d unique_frames=%d",
            nested_stats["iframe_count"],
            nested_stats["shadow_root_count"],
            nested_stats["unique_frame_ids"],
        )

    url = ""
    title = ""
    try:
        page = await browser_session.get_current_page()
        url = page.url if page else ""
        title = await page.title() if page else ""
    except (RuntimeError, OSError, AttributeError):
        pass

    return {
        "element_tree": element_tree_text,
        "selector_map": selector_map,
        "url": url,
        "title": title,
        "iframe_count": nested_stats["iframe_count"],
        "shadow_root_count": nested_stats["shadow_root_count"],
    }


def serialize_axtree(tree: dict) -> str:
    text: str = tree.get("element_tree", "")
    if not text:
        return "(empty page or no interactive elements found)"

    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + f"\n...[truncated, original length: {len(tree['element_tree'])} chars]"

    return text


def extract_interactive_elements(tree: dict) -> list[dict]:
    selector_map = tree.get("selector_map", {})
    return [
        {
            "ref": element.get("ref", str(ref_id)),
            "role": element.get("role", "unknown"),
            "name": element.get("name", ""),
            "attributes": element.get("attributes", {}),
            **({"frame_id": element["frame_id"]} if "frame_id" in element else {}),
            **({"shadow_root_type": element["shadow_root_type"]} if "shadow_root_type" in element else {}),
        }
        for ref_id, element in selector_map.items()
    ]


def axtree_to_markdown(tree: dict) -> str:
    url = tree.get("url", "")
    title = tree.get("title", "")
    content = serialize_axtree(tree)

    parts = []
    if title:
        parts.append(f"# {title}")
    if url:
        parts.append(f"URL: {url}")

    iframe_count = tree.get("iframe_count", 0)
    shadow_root_count = tree.get("shadow_root_count", 0)
    if iframe_count or shadow_root_count:
        parts.append(f"Nested contexts: {iframe_count} iframe(s), {shadow_root_count} shadow root(s)")

    parts.append("")
    parts.append("## Interactive Elements")
    parts.append("")
    parts.append(content)

    return "\n".join(parts)
