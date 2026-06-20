from __future__ import annotations

from typing import Any

_SVG_ICON_ROLES = frozenset({"img", "image", "graphics-symbol", "graphics-document"})
_SVG_ICON_TAGS = frozenset({"svg", "path", "circle", "rect", "polygon", "polyline", "use", "g", "icon"})


def is_visible(node: dict[str, Any]) -> bool:
    attrs = node.get("attributes") or {}
    if not isinstance(attrs, dict):
        return True

    style = attrs.get("style") or {}
    if isinstance(style, dict):
        if style.get("display") == "none":
            return False
        if style.get("visibility") == "hidden":
            return False
        opacity = style.get("opacity")
        if opacity is not None:
            try:
                if float(opacity) == 0.0:
                    return False
            except (ValueError, TypeError):
                pass

    hidden_val = attrs.get("hidden")
    if hidden_val not in (None, False, "false", 0, "0"):
        return False

    if attrs.get("aria-hidden") == "true":
        return False

    bbox = node.get("bbox") or {}
    return not (isinstance(bbox, dict) and bbox and bbox.get("width", 1) == 0 and bbox.get("height", 1) == 0)


def is_occluded(node: dict[str, Any], all_nodes: list[dict[str, Any]]) -> bool:
    bbox = node.get("bbox") or {}
    if not isinstance(bbox, dict) or not bbox:
        return False

    x1 = bbox.get("x", 0)
    y1 = bbox.get("y", 0)
    w1 = bbox.get("width", 0)
    h1 = bbox.get("height", 0)

    if w1 == 0 or h1 == 0:
        return False

    node_style = (node.get("attributes") or {}).get("style") or {}
    z1 = _parse_int(node_style.get("z-index", 0))

    for other in all_nodes:
        if other is node:
            continue
        other_bbox = other.get("bbox") or {}
        if not isinstance(other_bbox, dict) or not other_bbox:
            continue

        x2 = other_bbox.get("x", 0)
        y2 = other_bbox.get("y", 0)
        w2 = other_bbox.get("width", 0)
        h2 = other_bbox.get("height", 0)

        other_style = (other.get("attributes") or {}).get("style") or {}
        z2 = _parse_int(other_style.get("z-index", 0))

        if z2 <= z1:
            continue

        if x2 <= x1 and y2 <= y1 and (x2 + w2) >= (x1 + w1) and (y2 + h2) >= (y1 + h1):
            return True

    return False


def dedupe_by_bbox(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bbox_groups: dict[tuple[float, float, float, float], dict[str, Any]] = {}
    no_bbox: list[dict[str, Any]] = []

    for node in nodes:
        bbox = node.get("bbox") or {}
        if not isinstance(bbox, dict) or not bbox:
            no_bbox.append(node)
            continue

        key = (
            float(bbox.get("x", 0)),
            float(bbox.get("y", 0)),
            float(bbox.get("width", 0)),
            float(bbox.get("height", 0)),
        )

        if key not in bbox_groups:
            bbox_groups[key] = node
        else:
            existing_name = str(bbox_groups[key].get("name") or "")
            new_name = str(node.get("name") or "")
            if len(new_name) > len(existing_name):
                bbox_groups[key] = node

    return list(bbox_groups.values()) + no_bbox


def collapse_svg_icons(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    i = 0
    while i < len(nodes):
        if not _is_svg_icon(nodes[i]):
            result.append(nodes[i])
            i += 1
            continue

        group_start = i
        while i < len(nodes) and _is_svg_icon(nodes[i]):
            i += 1

        group = nodes[group_start:i]
        if len(group) == 1:
            result.append(group[0])
        else:
            result.append({
                "ref": group[0].get("ref", str(group_start)),
                "role": "icon_group",
                "name": f"icon group ({len(group)} icons)",
                "attributes": {},
                "_collapsed_count": len(group),
            })

    return result


def prune_selector_map(selector_map: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _empty_meta: dict[str, Any] = {"original_count": 0, "pruned_count": 0, "pruning_ratio": 0.0}

    if not isinstance(selector_map, dict):
        return {}, _empty_meta

    original_count = len(selector_map)
    if original_count == 0:
        return {}, _empty_meta

    visible_items = {k: v for k, v in selector_map.items() if is_visible(v)}

    all_visible = list(visible_items.values())
    non_occluded_items = {k: v for k, v in visible_items.items() if not is_occluded(v, all_visible)}

    deduped = dedupe_by_bbox(list(non_occluded_items.values()))
    collapsed = collapse_svg_icons(deduped)

    pruned_map: dict[str, Any] = {}
    for node in collapsed:
        ref = str(node.get("ref", id(node)))
        pruned_map[ref] = node

    pruned_count = len(pruned_map)
    pruning_ratio = round(1.0 - pruned_count / original_count, 4) if original_count > 0 else 0.0

    return pruned_map, {
        "original_count": original_count,
        "pruned_count": pruned_count,
        "pruning_ratio": pruning_ratio,
    }


def _parse_int(value: Any) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _is_svg_icon(node: dict[str, Any]) -> bool:
    role = str(node.get("role") or "").lower()
    if role in _SVG_ICON_ROLES:
        return True
    attrs = node.get("attributes") or {}
    tag = str(attrs.get("tag") or "").lower()
    return tag in _SVG_ICON_TAGS
