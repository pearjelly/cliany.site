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
    pending = [root]
    visited = 0
    while pending and len(candidates) < limit and visited < 5000:
        node = pending.pop()
        visited += 1
        pending.extend(reversed(getattr(node, "children_nodes", None) or []))
        if getattr(node, "is_visible", None) is False:
            continue

        ax_node = getattr(node, "ax_node", None)
        role = _to_text(getattr(ax_node, "role", "")).lower()
        if role not in _READ_ONLY_EXTRACT_ROLES:
            continue
        tag = _to_text(getattr(node, "tag_name", "")).lower()
        attributes = getattr(node, "attributes", None)
        if not isinstance(attributes, dict):
            continue
        selectors = [
            selector
            for selector in compute_selector_candidates(tag, attributes)
            if selector.startswith(("#", '[data-testid="', '[aria-label="'))
        ][:2]
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
        name = _to_text(item.get("name")).replace("\n", " ").replace('"', '\\"')
        text = _to_text(item.get("text")).replace("\n", " ").replace('"', '\\"')
        selectors = item.get("selectors")
        if not role or not isinstance(selectors, list) or not selectors:
            continue
        line = f'[{role} "{name}" text="{text}"] → {", ".join(str(value) for value in selectors)}'
        if len("\n".join([*lines, line])) > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


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
