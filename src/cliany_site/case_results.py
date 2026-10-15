"""Validate the declared result rows of a maintained read-only case."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def check_case_rows(payload: Any, expectation: Mapping[str, Any]) -> dict[str, Any]:
    path, minimum = expectation.get("path"), expectation.get("min_count")
    if (not isinstance(path, list) or not path or not all(isinstance(key, str) and key for key in path)
            or type(minimum) is not int or minimum < 0):
        raise ValueError("expected_rows requires a key path and nonnegative integer min_count")
    fields = expectation.get("required_fields", [])
    if "required_fields" in expectation and (
        not isinstance(fields, list) or not fields
        or not all(isinstance(field, str) and field.strip() for field in fields)
        or len(fields) != len(set(fields))
    ):
        raise ValueError("required_fields must declare unique nonempty text field names")
    rows = payload
    for key in path:
        rows = rows.get(key) if isinstance(rows, dict) else None
    if not isinstance(rows, list) or not all(isinstance(row, dict) and row for row in rows):
        return {"ok": False, "status": "invalid_rows", "row_count": None, "min_count": minimum}
    invalid_fields = {}
    for field in fields:
        invalid_rows = [index + 1 for index, row in enumerate(rows)
                        if not isinstance(row.get(field), str) or not row[field].strip()]
        if invalid_rows:
            invalid_fields[field] = invalid_rows
    if invalid_fields:
        return {"ok": False, "status": "invalid_fields", "row_count": len(rows), "min_count": minimum,
                "field_invalid_rows": invalid_fields}
    return {"ok": len(rows) >= minimum, "status": "ok" if len(rows) >= minimum else "too_few_rows",
            "row_count": len(rows), "min_count": minimum}
