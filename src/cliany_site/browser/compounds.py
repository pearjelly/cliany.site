from __future__ import annotations

_SELECT_ROLES: frozenset[str] = frozenset({"select", "combobox", "listbox"})
_DATE_TYPES: frozenset[str] = frozenset({"date", "datetime-local", "time"})
_MAX_OPTIONS = 50


def extract_select_options(node: dict) -> dict | None:
    if node.get("role") not in _SELECT_ROLES:
        return None
    attrs = node.get("attributes") or {}
    raw = attrs.get("options")
    if not isinstance(raw, list):
        raw = []
    truncated = len(raw) > _MAX_OPTIONS
    return {"options": raw[:_MAX_OPTIONS], "truncated": truncated}


def extract_date_format(node: dict) -> dict | None:
    attrs = node.get("attributes") or {}
    input_type = attrs.get("type", "")
    if input_type not in _DATE_TYPES:
        return None
    result: dict = {"type": input_type}
    for key in ("min", "max", "pattern"):
        val = attrs.get(key)
        if val is not None:
            result[key] = val
    return result


def extract_file_accept(node: dict) -> dict | None:
    attrs = node.get("attributes") or {}
    if attrs.get("type") != "file":
        return None
    return {
        "accept": attrs.get("accept", ""),
        "multiple": bool(attrs.get("multiple", False)),
    }


def extract_compounds(selector_map: dict) -> dict:
    result: dict = {}
    for ref_id, node in selector_map.items():
        compound: dict = {}
        sel = extract_select_options(node)
        if sel is not None:
            compound["select_options"] = sel
        dat = extract_date_format(node)
        if dat is not None:
            compound["date_format"] = dat
        fil = extract_file_accept(node)
        if fil is not None:
            compound["file_accept"] = fil
        if compound:
            result[str(ref_id)] = compound
    return result
