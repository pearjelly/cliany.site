from __future__ import annotations

import re
from typing import Any

_TAILWIND_WHITELIST_RE = re.compile(
    r"^(text|bg|flex|grid|p[trblxy]?|m[trblxy]?|w|h|min|max|rounded|border|shadow|font|leading|tracking)-"
)
_DYNAMIC_CLASS_PATTERNS = (
    re.compile(r"^css-"),
    re.compile(r"^sc-"),
    re.compile(r"^_[a-z0-9]{4,}$"),
    re.compile(r"^[a-z]{1,2}[A-Z][a-zA-Z0-9]{3,}$"),
    re.compile(r"^[a-f0-9]{5,}$", re.IGNORECASE),
)
_RANDOM_ID_PATTERNS = (
    re.compile(r"^[a-f0-9]{6,}$", re.IGNORECASE),
    re.compile(r"^[a-f0-9]{4,}-[a-f0-9]{4,}", re.IGNORECASE),
)
_ROLE_TO_TAG: dict[str, str] = {
    "button": "button",
    "link": "a",
    "textbox": "input",
    "searchbox": "input",
    "combobox": "select",
    "checkbox": "input",
    "radio": "input",
    "img": "img",
    "image": "img",
    "form": "form",
    "list": "ul",
    "listitem": "li",
    "table": "table",
    "row": "tr",
    "cell": "td",
    "navigation": "nav",
    "banner": "header",
    "main": "main",
    "contentinfo": "footer",
    "article": "article",
    "dialog": "dialog",
}


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _escape_attr_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_css_identifier(value: str) -> str:
    return re.sub(r"([^a-zA-Z0-9_-])", r"\\\1", value)


def _is_random_id(value: str) -> bool:
    return any(pattern.match(value) for pattern in _RANDOM_ID_PATTERNS)


def _is_stable_class(class_name: str) -> bool:
    if not class_name:
        return False
    if _TAILWIND_WHITELIST_RE.match(class_name):
        return True
    return not any(pattern.match(class_name) for pattern in _DYNAMIC_CLASS_PATTERNS)


def _infer_tag_from_role(role: str) -> str:
    role_text = _to_text(role).lower()
    if not role_text or role_text == "unknown":
        return ""
    if role_text in _ROLE_TO_TAG:
        return _ROLE_TO_TAG[role_text]
    if re.match(r"^[a-z][a-z0-9-]*$", role_text):
        return role_text
    return ""


def compute_selector_candidates(tag: str, attributes: dict[str, str], ref_id: str = "") -> list[str]:
    _ = ref_id
    attrs = attributes if isinstance(attributes, dict) else {}
    normalized_tag = _to_text(tag).lower()

    candidates: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        value = _to_text(candidate)
        if value and value not in seen:
            seen.add(value)
            candidates.append(value)

    testid = _to_text(attrs.get("data-testid"))
    if testid:
        add(f'[data-testid="{_escape_attr_value(testid)}"]')

    element_id = _to_text(attrs.get("id"))
    if element_id and not _is_random_id(element_id):
        add(f"#{_escape_css_identifier(element_id)}")

    aria_label = _to_text(attrs.get("aria-label"))
    if aria_label:
        add(f'[aria-label="{_escape_attr_value(aria_label)}"]')

    class_attr = _to_text(attrs.get("class"))
    if normalized_tag and class_attr:
        stable_classes = [
            class_name for class_name in re.split(r"\s+", class_attr) if class_name and _is_stable_class(class_name)
        ]
        for class_name in stable_classes:
            add(f"{normalized_tag}.{_escape_css_identifier(class_name)}")

    placeholder = _to_text(attrs.get("placeholder"))
    if normalized_tag and placeholder:
        add(f'{normalized_tag}[placeholder="{_escape_attr_value(placeholder)}"]')

    if normalized_tag:
        add(normalized_tag)

    return candidates


def enrich_selector_map(selector_map: dict[str, dict]) -> dict[str, dict]:
    if not isinstance(selector_map, dict):
        return {}

    for key, entry in selector_map.items():
        if not isinstance(entry, dict):
            continue

        raw_attributes = entry.get("attributes")
        attributes = raw_attributes if isinstance(raw_attributes, dict) else {}
        tag = _to_text(attributes.get("tag")).lower() or _infer_tag_from_role(_to_text(entry.get("role")))
        ref_id = _to_text(entry.get("ref")) or str(key)

        entry["css_candidates"] = compute_selector_candidates(tag, attributes, ref_id=ref_id)

    return selector_map


_READ_ONLY_EXTRACT_ROLES = frozenset({"status", "alert", "list", "table"})


def collect_read_only_extract_candidates(root: Any, limit: int = 20) -> list[dict[str, Any]]:
    """Ground extract selectors in visible AX semantics and observed DOM attributes."""
    if root is None or limit <= 0:
        return []

    candidates: list[dict[str, Any]] = []
    pending = [(root, None)]
    visited = 0
    semantic_nodes: list[tuple[str, str, Any, dict[str, Any], Any]] = []
    tag_counts: dict[str, int] = {}
    while pending and visited < 5000:
        node, parent = pending.pop()
        visited += 1
        if getattr(node, "is_visible", None) is False:
            continue
        pending.extend((child, node) for child in reversed(getattr(node, "children_nodes", None) or []))
        tag = _to_text(getattr(node, "tag_name", "")).lower()
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

        ax_node = getattr(node, "ax_node", None)
        role = _to_text(getattr(ax_node, "role", "")).lower()
        if role not in _READ_ONLY_EXTRACT_ROLES:
            continue
        attributes = getattr(node, "attributes", None)
        if not isinstance(attributes, dict):
            continue
        semantic_nodes.append((role, tag, node, attributes, parent))

    for role, tag, node, attributes, parent in semantic_nodes:
        if len(candidates) >= limit:
            break
        selectors = [
            selector
            for selector in compute_selector_candidates(tag, attributes)
            if selector.startswith(("#", '[data-testid="', '[aria-label="'))
        ][:2]
        if tag == "output" and tag_counts[tag] == 1:
            selectors.append(tag)
        elif not selectors and tag in {"ul", "ol", "table"} and tag_counts[tag] == 1:
            selectors = [tag]
        if not selectors and parent is not None and tag in {"ul", "ol", "table"}:
            siblings = getattr(parent, "children_nodes", None) or []
            same_kind = sum(
                _to_text(getattr(sibling, "tag_name", "")).lower() in {"ul", "ol", "table"}
                for sibling in siblings
            )
            if same_kind == 1:
                parent_attrs = getattr(parent, "attributes", None)
                if isinstance(parent_attrs, dict):
                    parent_tag = _to_text(getattr(parent, "tag_name", "")).lower()
                    anchors = [
                        value for value in compute_selector_candidates(parent_tag, parent_attrs)
                        if value.startswith(("#", '[data-testid="', '[aria-label="'))
                    ]
                    child_tag = "tr" if tag == "table" else "li"
                    selectors = [f"{anchor} {child_tag}" for anchor in anchors[:2]]
        if not selectors:
            continue
        name = _to_text(getattr(ax_node, "name", ""))
        text = _to_text(node.get_all_children_text()) if hasattr(node, "get_all_children_text") else ""
        if not name and not text and role not in {"list", "table"}:
            continue
        candidates.append({"role": role, "name": name[:80], "text": text[:120], "selectors": selectors})
    return candidates


def format_read_only_extract_candidates(candidates: list[dict[str, Any]], max_chars: int = 2000) -> str:
    lines: list[str] = []
    for item in candidates:
        role = _to_text(item.get("role"))
        name = _to_text(item.get("name")).replace("\n", " ").replace("\r", " ").replace('"', '\\"')
        text = _to_text(item.get("text")).replace("\n", " ").replace("\r", " ").replace('"', '\\"')
        selectors = item.get("selectors")
        if not role or not isinstance(selectors, list) or not selectors:
            continue
        line = f'[{role} "{name}" text="{text}"] → {", ".join(str(value) for value in selectors)}'
        if len("\n".join([*lines, line])) > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


def is_grounded_extract_selector(selector: str, selector_map: dict[str, dict], extract_candidates: list[dict]) -> bool:
    """Accept only selectors observed in this AX snapshot or a semantic list/table child."""
    value = _to_text(selector)
    if not value:
        return False

    for entry in selector_map.values():
        if isinstance(entry, dict) and value in (entry.get("css_candidates") or []):
            return True

    for item in extract_candidates:
        if not isinstance(item, dict):
            continue
        selectors = item.get("selectors")
        if not isinstance(selectors, list):
            continue
        for root in selectors:
            if not isinstance(root, str) or not root:
                continue
            if value == root:
                return True
            if item.get("role") == "list" and value == f"{root} li":
                return True
            if item.get("role") == "table" and value == f"{root} tr":
                return True
    return False


def format_selector_candidates_section(selector_map: dict[str, dict], max_chars: int = 3000) -> str:
    if not isinstance(selector_map, dict):
        return ""

    lines: list[str] = []
    for key, entry in selector_map.items():
        if not isinstance(entry, dict):
            continue

        raw_candidates = entry.get("css_candidates")
        if not isinstance(raw_candidates, list):
            continue

        candidates = [_to_text(item) for item in raw_candidates if _to_text(item)]
        if not candidates:
            continue

        ref = _to_text(entry.get("ref")) or str(key)
        role = _to_text(entry.get("role"))
        name = _to_text(entry.get("name")).replace('"', '\\"').replace("\n", " ").replace("\r", " ")
        lines.append(f'@{ref} [{role} "{name}"] → {", ".join(candidates)}')

    if not lines:
        return ""

    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered

    if max_chars <= 0:
        return f"...[还有 {len(lines)} 个元素]"

    included: list[str] = []
    for index, line in enumerate(lines):
        next_block = "\n".join([*included, line]) if included else line
        remaining_count = len(lines) - (index + 1)
        if remaining_count > 0:
            suffix = f"...[还有 {remaining_count} 个元素]"
            trial = f"{next_block}\n{suffix}"
        else:
            trial = next_block

        if len(trial) <= max_chars:
            included.append(line)
            continue
        break

    remaining = len(lines) - len(included)
    if remaining <= 0:
        return "\n".join(included)

    suffix = f"...[还有 {remaining} 个元素]"
    if not included:
        return suffix if len(suffix) <= max_chars else suffix[:max_chars]

    body = "\n".join(included)
    while included and len(f"{body}\n{suffix}") > max_chars:
        included.pop()
        body = "\n".join(included)

    if not included:
        return suffix if len(suffix) <= max_chars else suffix[:max_chars]

    return f"{body}\n{suffix}"
