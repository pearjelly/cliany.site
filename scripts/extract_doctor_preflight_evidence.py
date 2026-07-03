#!/usr/bin/env python3
"""Extract candidate-promotion doctor preflight evidence from doctor JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_cases  # noqa: E402

NAMED_LIST_RE = re.compile(r'^(?P<field>\w+)\[name="(?P<name>[^"]+)"\]$')


def _stable_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resolve_selector(payload: Any, selector: str) -> Any:
    current = payload
    for part in selector.split("."):
        if not part:
            return None
        match = NAMED_LIST_RE.match(part)
        if match:
            if not isinstance(current, dict):
                return None
            items = current.get(match.group("field"))
            if not isinstance(items, list):
                return None
            current = next(
                (
                    item
                    for item in items
                    if isinstance(item, dict) and item.get("name") == match.group("name")
                ),
                None,
            )
            if current is None:
                return None
            continue
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def extract_payload(payload: dict[str, Any]) -> dict[str, Any]:
    selectors = dict(validate_cases.DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS)
    values = {
        field: _resolve_selector(payload, selector)
        for field, selector in selectors.items()
    }
    missing_fields = [field for field, value in values.items() if value is None]
    return {
        "schema_version": 1,
        "ok": not missing_fields,
        "field_count": len(selectors),
        "missing_count": len(missing_fields),
        "missing_fields": missing_fields,
        "fields": list(selectors),
        "selectors": selectors,
        "selectors_sha256": _stable_json_sha256(selectors),
        "values": values,
        "values_sha256": _stable_json_sha256(values),
    }


def extract_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{path} must contain a JSON object"
        raise ValueError(msg)
    evidence = extract_payload(payload)
    evidence["source_path"] = str(path)
    return evidence


def _markdown_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


def render_markdown(evidence: dict[str, Any]) -> str:
    values = evidence.get("values")
    values = values if isinstance(values, dict) else {}
    lines = [
        "## Doctor Preflight Evidence",
        "",
        f"- ok: `{str(bool(evidence.get('ok'))).lower()}`",
        f"- field_count: `{evidence.get('field_count')}`",
        f"- missing_count: `{evidence.get('missing_count')}`",
        f"- selectors_sha256: `{evidence.get('selectors_sha256')}`",
        f"- values_sha256: `{evidence.get('values_sha256')}`",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    for field, value in values.items():
        lines.append(f"| `{field}` | `{_markdown_value(value)}` |")
    missing_fields = evidence.get("missing_fields")
    if isinstance(missing_fields, list) and missing_fields:
        lines.extend(["", "## Missing Fields"])
        lines.extend(f"- `{field}`" for field in missing_fields)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract doctor preflight evidence fields from doctor JSON.",
    )
    parser.add_argument("doctor_json", type=Path)
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="输出可粘贴到 candidate issue 的 Markdown blocker evidence",
    )
    args = parser.parse_args(argv)

    evidence = extract_file(args.doctor_json)
    if args.markdown:
        print(render_markdown(evidence))
    else:
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
