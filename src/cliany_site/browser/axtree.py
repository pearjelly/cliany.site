"""
AXTree 捕获与序列化 — 包装 browser-use DomService API

DomService 需要 BrowserSession（非 Page）；get_serialized_dom_tree() 返回
tuple[SerializedDOMState, EnhancedDOMTreeNode, dict]；llm_representation() 生成
带 @ref 标记的可交互元素文本。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from browser_use.browser.session import BrowserSession

MAX_CHARS = 20_000


async def capture_axtree(browser_session: Any) -> dict:
    """
    从当前页面捕获 Accessibility Tree。

    Args:
        browser_session: browser-use BrowserSession 对象

    Returns:
        dict: element_tree (str), selector_map (dict), url (str), title (str)
    """
    from browser_use.dom.service import DomService

    dom_service = DomService(browser_session)
    serialized, _enhanced_tree, _timing = await dom_service.get_serialized_dom_tree()

    if hasattr(serialized, "selector_map") and serialized.selector_map:
        browser_session.update_cached_selector_map(serialized.selector_map)

    element_tree_text = serialized.llm_representation()

    selector_map: dict[str, dict] = {}
    if hasattr(serialized, "selector_map") and serialized.selector_map:
        for ref_id, element in serialized.selector_map.items():
            try:
                role = element.tag_name if hasattr(element, "tag_name") else "unknown"
                ax_name = ""
                if hasattr(element, "ax_node") and element.ax_node is not None:
                    ax_name = getattr(element.ax_node, "name", "") or ""
                if not ax_name:
                    ax_name = (
                        element.node_value if hasattr(element, "node_value") else ""
                    )
                selector_map[str(ref_id)] = {
                    "ref": str(ref_id),
                    "role": role,
                    "name": ax_name,
                    "attributes": dict(getattr(element, "attributes", {}) or {}),
                }
            except Exception:
                selector_map[str(ref_id)] = {"ref": str(ref_id)}

    url = ""
    title = ""
    try:
        page = await browser_session.get_current_page()
        url = page.url if page else ""
        title = await page.title() if page else ""
    except Exception:
        pass

    return {
        "element_tree": element_tree_text,
        "selector_map": selector_map,
        "url": url,
        "title": title,
    }


def serialize_axtree(tree: dict) -> str:
    text = tree.get("element_tree", "")
    if not text:
        return "(empty page or no interactive elements found)"

    if len(text) > MAX_CHARS:
        text = (
            text[:MAX_CHARS]
            + f"\n...[truncated, original length: {len(tree['element_tree'])} chars]"
        )

    return text


def extract_interactive_elements(tree: dict) -> list[dict]:
    selector_map = tree.get("selector_map", {})
    return [
        {
            "ref": element.get("ref", str(ref_id)),
            "role": element.get("role", "unknown"),
            "name": element.get("name", ""),
            "attributes": element.get("attributes", {}),
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
    parts.append("")
    parts.append("## Interactive Elements")
    parts.append("")
    parts.append(content)

    return "\n".join(parts)
