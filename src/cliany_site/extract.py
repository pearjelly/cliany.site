"""
extract.py — 将 extract action 参数转换为可在 Page.evaluate() 中执行的 JS 表达式。

所有生成的 JS 必须是箭头函数格式（() => ...），以满足 browser_use Page.evaluate() 的要求。
"""

from __future__ import annotations

import json
from typing import Any

SUPPORTED_EXTRACT_MODES = ("text", "list", "table", "attribute")


def _coerce_json_like_extract_data(raw_result: Any) -> Any:
    if not isinstance(raw_result, str):
        return raw_result

    text = raw_result.strip()
    if not text or text[:1] not in {"[", "{"}:
        return raw_result

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return raw_result


def _escape_selector(selector: str) -> str:
    return selector.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")


def _parse_field_spec(spec: str) -> tuple[str, str | None]:
    if "@" in spec:
        css_selector, attr_name = spec.rsplit("@", 1)
        css_selector = css_selector.strip()
        attr_name = attr_name.strip()
        return css_selector, (attr_name or None)
    return spec.strip(), None


def _normalize_fields_map(fields_map: dict | None) -> dict[str, str]:
    if fields_map is None:
        return {}
    if not isinstance(fields_map, dict):
        raise ValueError("fields_map 必须是 dict 或 None")
    normalized: dict[str, str] = {}
    for field_name, field_spec in fields_map.items():
        normalized[str(field_name)] = str(field_spec)
    return normalized


def _build_nested_field_extract_expr(container_var: str, spec: str) -> str:
    css_selector, attr_name = _parse_field_spec(spec)
    escaped_css = _escape_selector(css_selector)

    if attr_name:
        escaped_attr = _escape_selector(attr_name)
        attr_name_lower = attr_name.lower()

        def _build_attr_fallback(container_expr: str) -> str:
            if attr_name_lower in {"href", "src"}:
                return f"({container_expr}.getAttribute('{escaped_attr}') || {container_expr}.{escaped_attr} || '')"

            return f"({container_expr}.getAttribute('{escaped_attr}') || '')"

        def _build_parent_scope_fallback(container_expr: str) -> str:
            if attr_name_lower not in {"href", "src"}:
                return ""

            return (
                f"const parent = {container_expr}.parentElement; "
                + "if (parent) { "
                + "const scoped = parent.querySelector('a[href], [href], [data-href], [data-url], [data-link]'); "
                + "if (scoped) return ("
                + "scoped.getAttribute('href') || "
                + "scoped.getAttribute('data-href') || "
                + "scoped.getAttribute('data-url') || "
                + "scoped.getAttribute('data-link') || "
                + "scoped.href || ''"
                + "); "
                + "} "
            )

        if escaped_css:
            return (
                "(() => { "
                + f"const t = {container_var}.querySelector('{escaped_css}'); "
                + f"if (t) {{ const v = {_build_attr_fallback('t')}; if (v) return v; }} "
                + f"const direct = {container_var}; "
                + f"if (direct) {{ const v = {_build_attr_fallback('direct')}; if (v) return v; }} "
                + f"const nearest = {container_var}.closest('a'); "
                + f"if (nearest) {{ const v = {_build_attr_fallback('nearest')}; if (v) return v; }} "
                + _build_parent_scope_fallback(container_var)
                + "return ''; "
                + "})()"
            )
        return (
            "(() => { "
            + f"const t = {container_var}; "
            + f"if (t) {{ const v = {_build_attr_fallback('t')}; if (v) return v; }} "
            + f"const nearest = {container_var}.closest('a'); "
            + f"if (nearest) {{ const v = {_build_attr_fallback('nearest')}; if (v) return v; }} "
            + _build_parent_scope_fallback(container_var)
            + "return ''; "
            + "})()"
        )

    if escaped_css:
        return (
            "(() => { "
            + f"const t = {container_var}.querySelector('{escaped_css}'); "
            + "if (t && t.textContent) return t.textContent.trim(); "
            + f"const direct = {container_var}; "
            + "return direct && direct.textContent ? direct.textContent.trim() : ''; "
            + "})()"
        )

    return (
        "(() => { "
        + f"const t = {container_var}; "
        + "return t ? (t.textContent ? t.textContent.trim() : '') : ''; "
        + "})()"
    )


def _build_text_js(selector: str) -> str:
    escaped_selector = _escape_selector(selector)
    return (
        "() => { "
        + f"const el = document.querySelector('{escaped_selector}'); "
        + "return el ? {text: (el.textContent ? el.textContent.trim() : '')} : {text: ''}; "
        + "}"
    )


def _build_attribute_js(selector: str, fields_map: dict | None = None) -> str:
    escaped_selector = _escape_selector(selector)
    normalized_fields = _normalize_fields_map(fields_map)

    if not normalized_fields:
        # 无 fields_map：返回元素所有属性的字典
        return (
            "() => { "
            + f"const el = document.querySelector('{escaped_selector}'); "
            + "return el ? Object.fromEntries(Array.from(el.attributes).map(a => [a.name, a.value])) : {}; "
            + "}"
        )

    # 有 fields_map：返回指定属性的字典
    lines = [
        "() => {",
        f"  const el = document.querySelector('{escaped_selector}');",
        "  if (!el) return {};",
        "  return {",
    ]
    for field_name, field_spec in normalized_fields.items():
        escaped_field_name = _escape_selector(field_name)
        _, attr_name = _parse_field_spec(field_spec)
        if attr_name:
            escaped_attr = _escape_selector(attr_name)
            lines.append(f"    '{escaped_field_name}': (el.getAttribute('{escaped_attr}') || ''),")
        else:
            lines.append(f"    '{escaped_field_name}': (el.textContent ? el.textContent.trim() : ''),")

    lines.extend(["  };", "}"])
    return "\n".join(lines)


def _build_list_js(selector: str, fields_map: dict | None) -> str:
    escaped_selector = _escape_selector(selector)
    normalized_fields = _normalize_fields_map(fields_map)

    if not normalized_fields:
        return (
            "() => { "
            + f"const items = Array.from(document.querySelectorAll('{escaped_selector}')).slice(0, 100); "
            + "return items.map(el => (el.textContent ? el.textContent.trim() : '')); "
            + "}"
        )

    lines = [
        "() => {",
        f"  const items = Array.from(document.querySelectorAll('{escaped_selector}')).slice(0, 100);",
        "  return items.map(el => ({",
    ]

    for field_name, field_spec in normalized_fields.items():
        escaped_field_name = _escape_selector(field_name)
        field_expr = _build_nested_field_extract_expr("el", field_spec)
        lines.append(f"    '{escaped_field_name}': {field_expr},")

    lines.extend(["  }));", "}"])
    return "\n".join(lines)


def _build_table_js(selector: str, fields_map: dict | None) -> str:
    escaped_selector = _escape_selector(selector)
    normalized_fields = _normalize_fields_map(fields_map)

    if normalized_fields:
        lines = [
            "() => {",
            f"  const table = document.querySelector('{escaped_selector}');",
            "  if (!table) return [];",
            "  const rows = Array.from(table.querySelectorAll('tr')).slice(1, 501);",
            "  return rows.map(row => ({",
        ]

        for field_name, field_spec in normalized_fields.items():
            escaped_field_name = _escape_selector(field_name)
            field_expr = _build_nested_field_extract_expr("row", field_spec)
            lines.append(f"    '{escaped_field_name}': {field_expr},")

        lines.extend(["  }));", "}"])
        return "\n".join(lines)

    return "\n".join(
        [
            "() => {",
            f"  const table = document.querySelector('{escaped_selector}');",
            "  if (!table) return [];",
            "  const rows = Array.from(table.querySelectorAll('tr')).slice(0, 501);",
            "  return rows.map(row => Array.from(row.querySelectorAll('td,th')).map("
            "cell => (cell.textContent ? cell.textContent.trim() : '')));",
            "}",
        ]
    )


def build_extract_js(selector: str, mode: str, fields_map: dict | None = None) -> str:
    """
    根据 extract action 参数，生成可传入 Page.evaluate() 的 JS 箭头函数字符串。

    Args:
        selector: CSS 选择器，用于定位目标元素
        mode: 提取模式，支持 text / list / table / attribute
        fields_map: 字段映射，key 是字段名，value 是 CSS 选择器或 "@attr" 语法

    Returns:
        可直接传入 Page.evaluate() 的 JS 箭头函数字符串。
        - text 模式：返回 {text: "..."} 对象
        - attribute 模式（无 fields_map）：返回元素所有属性的字典 {name: value, ...}
        - attribute 模式（有 fields_map）：返回指定属性的字典
        - list 模式（有 fields_map）：返回对象数组 [{field: value, ...}, ...]
        - table 模式（无 fields_map）：返回 2D 数组 [["cell", ...], ...]
        - table 模式（有 fields_map）：返回对象数组 [{field: value, ...}, ...]
    """
    if not isinstance(selector, str) or not selector.strip():
        raise ValueError("selector 不能为空")

    normalized_mode = str(mode or "").strip().lower()
    normalized_selector = selector.strip()

    if normalized_mode == "text":
        return _build_text_js(normalized_selector)
    if normalized_mode == "attribute":
        return _build_attribute_js(normalized_selector, fields_map)
    if normalized_mode == "list":
        return _build_list_js(normalized_selector, fields_map)
    if normalized_mode == "table":
        return _build_table_js(normalized_selector, fields_map)

    supported = ", ".join(SUPPORTED_EXTRACT_MODES)
    raise ValueError(f"不支持的提取模式: {mode}，支持: {supported}")
