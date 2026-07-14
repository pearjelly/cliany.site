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
MISSING_SELECTOR_VALUE = object()
READY_NEXT_ACTION = (
    "Run the candidate explore command, then package the adapter and attach "
    "the package path or release asset name."
)
BLOCKED_NEXT_ACTION = (
    "Attach the doctor preflight evidence to the candidate issue and do "
    "not run candidate explore until live preflight is ready."
)
MISSING_FIELDS_NEXT_ACTION = (
    "Attach the missing field list and original doctor JSON summary before "
    "continuing candidate promotion."
)
EXTRACTOR_CONTRACT_FIELDS = (
    "summary.llm_live_preflight",
    "checks[llm_live].details.status_code",
)


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
            return MISSING_SELECTOR_VALUE
        match = NAMED_LIST_RE.match(part)
        if match:
            if not isinstance(current, dict):
                return MISSING_SELECTOR_VALUE
            items = current.get(match.group("field"))
            if not isinstance(items, list):
                return MISSING_SELECTOR_VALUE
            current = next(
                (
                    item
                    for item in items
                    if isinstance(item, dict) and item.get("name") == match.group("name")
                ),
                MISSING_SELECTOR_VALUE,
            )
            if current is MISSING_SELECTOR_VALUE:
                return MISSING_SELECTOR_VALUE
            continue
        if not isinstance(current, dict) or part not in current:
            return MISSING_SELECTOR_VALUE
        current = current[part]
    return current


def _build_preflight_state(
    values: dict[str, Any],
    missing_fields: list[str],
) -> dict[str, Any]:
    if missing_fields:
        return {
            "status": "missing_fields",
            "ready_for_adapter_package": False,
            "primary_reason": f"Missing required doctor evidence field: {missing_fields[0]}.",
            "reason_codes": ["missing_fields"],
            "next_action": MISSING_FIELDS_NEXT_ACTION,
        }

    checks = [
        (
            values.get("summary.ready_for_explore") is True,
            "ready_for_explore_false",
            "Doctor summary is not ready for explore.",
        ),
        (
            isinstance(values.get("summary.llm_live_preflight"), dict)
            and values["summary.llm_live_preflight"].get("ready") is True,
            "llm_live_preflight_not_ready",
            "Doctor LLM live preflight summary is not ready.",
        ),
        (
            values.get("summary.capabilities.run_browser_workflows.ready") is True,
            "run_browser_workflows_not_ready",
            "Browser workflow capability is not ready.",
        ),
        (
            values.get("summary.capabilities.generate_adapters.ready") is True,
            "generate_adapters_not_ready",
            "Adapter generation capability is not ready.",
        ),
        (
            values.get("checks[cdp].status") == "ok",
            f"cdp_status_{values.get('checks[cdp].status')}",
            f"CDP check is {values.get('checks[cdp].status')}.",
        ),
        (
            values.get("checks[llm_live].status") == "ok",
            f"llm_live_status_{values.get('checks[llm_live].status')}",
            f"Live LLM preflight is {values.get('checks[llm_live].status')}.",
        ),
    ]
    failures = [
        {"reason_code": reason_code, "reason": reason}
        for ok, reason_code, reason in checks
        if not ok
    ]
    if failures:
        return {
            "status": "blocked",
            "ready_for_adapter_package": False,
            "primary_reason": failures[-1]["reason"],
            "reason_codes": [failure["reason_code"] for failure in failures],
            "next_action": BLOCKED_NEXT_ACTION,
        }

    return {
        "status": "ready",
        "ready_for_adapter_package": True,
        "primary_reason": "Doctor preflight is ready for candidate adapter generation.",
        "reason_codes": [],
        "next_action": READY_NEXT_ACTION,
    }


def extract_payload(payload: dict[str, Any]) -> dict[str, Any]:
    selectors = dict(validate_cases.DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS)
    resolved_values = {
        field: _resolve_selector(payload, selector)
        for field, selector in selectors.items()
    }
    missing_fields = [
        field
        for field, value in resolved_values.items()
        if value is MISSING_SELECTOR_VALUE
    ]
    null_fields = [
        field
        for field, value in resolved_values.items()
        if value is None
    ]
    values = {
        field: None if value is MISSING_SELECTOR_VALUE else value
        for field, value in resolved_values.items()
    }
    return {
        "schema_version": 1,
        "ok": not missing_fields,
        "field_count": len(selectors),
        "missing_count": len(missing_fields),
        "missing_fields": missing_fields,
        "null_count": len(null_fields),
        "null_fields": null_fields,
        "fields": list(selectors),
        "selectors": selectors,
        "selectors_sha256": _stable_json_sha256(selectors),
        "values": values,
        "values_sha256": _stable_json_sha256(values),
        "preflight_state": _build_preflight_state(values, missing_fields),
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
    preflight_state = evidence.get("preflight_state")
    preflight_state = preflight_state if isinstance(preflight_state, dict) else {}
    lines = [
        "## Doctor Preflight Evidence",
        "",
        f"- ok: `{str(bool(evidence.get('ok'))).lower()}`",
        f"- field_count: `{evidence.get('field_count')}`",
        f"- missing_count: `{evidence.get('missing_count')}`",
        f"- null_count: `{evidence.get('null_count')}`",
        f"- selectors_sha256: `{evidence.get('selectors_sha256')}`",
        f"- values_sha256: `{evidence.get('values_sha256')}`",
        f"- preflight_status: `{preflight_state.get('status', '-')}`",
        (
            "- ready_for_adapter_package: "
            f"`{str(bool(preflight_state.get('ready_for_adapter_package'))).lower()}`"
        ),
        f"- preflight_primary_reason: `{preflight_state.get('primary_reason', '-')}`",
        f"- preflight_next_action: `{preflight_state.get('next_action', '-')}`",
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
    null_fields = evidence.get("null_fields")
    if isinstance(null_fields, list) and null_fields:
        lines.extend(["", "## Null Fields"])
        lines.extend(f"- `{field}`" for field in null_fields)
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
