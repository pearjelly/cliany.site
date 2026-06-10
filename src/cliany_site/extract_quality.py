from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractQuality:
    ok: bool
    status: str
    issues: list[str]
    row_count: int | None = None
    field_names: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ok": self.ok,
            "status": self.status,
            "issues": self.issues,
        }
        if self.row_count is not None:
            data["row_count"] = self.row_count
        if self.field_names is not None:
            data["field_names"] = self.field_names
        return data


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Mapping):
        return all(_is_blank(item) for item in value.values())
    if isinstance(value, list | tuple):
        return all(_is_blank(item) for item in value)
    return False


def _expected_fields(fields_map: Mapping[str, Any] | None) -> list[str]:
    if not fields_map:
        return []
    return [str(field_name) for field_name in fields_map]


def _finish(issues: list[str], *, row_count: int | None = None, field_names: list[str] | None = None) -> ExtractQuality:
    if not issues:
        return ExtractQuality(ok=True, status="ok", issues=[], row_count=row_count, field_names=field_names)
    status = "empty" if any(issue.startswith("empty") or issue.startswith("all ") for issue in issues) else "partial"
    return ExtractQuality(ok=False, status=status, issues=issues, row_count=row_count, field_names=field_names)


def _evaluate_text(data: Any) -> ExtractQuality:
    value = data.get("text") if isinstance(data, Mapping) else data
    issues = ["empty text"] if _is_blank(value) else []
    return _finish(issues)


def _evaluate_attribute(data: Any, expected: list[str]) -> ExtractQuality:
    if not isinstance(data, Mapping):
        return ExtractQuality(ok=False, status="empty", issues=["attribute result is not an object"])
    field_names = sorted(str(field) for field in data)
    if not data:
        return ExtractQuality(ok=False, status="empty", issues=["empty attribute object"], field_names=field_names)

    issues: list[str] = []
    for field in expected:
        if field not in data:
            issues.append(f"missing field: {field}")
        elif _is_blank(data.get(field)):
            issues.append(f"blank field: {field}")
    if not expected and all(_is_blank(value) for value in data.values()):
        issues.append("all attribute values are blank")
    return _finish(issues, field_names=field_names)


def _evaluate_dict_rows(rows: list[Mapping[str, Any]], expected: list[str]) -> ExtractQuality:
    field_names = sorted({str(field) for row in rows for field in row})
    check_fields = expected or field_names
    issues: list[str] = []

    if all(_is_blank(row) for row in rows):
        issues.append("all rows are blank")

    for field in check_fields:
        blank_count = sum(1 for row in rows if field not in row or _is_blank(row.get(field)))
        if blank_count == len(rows):
            issues.append(f"field is blank in all rows: {field}")
        elif blank_count:
            issues.append(f"field is blank in {blank_count}/{len(rows)} rows: {field}")

    return _finish(issues, row_count=len(rows), field_names=field_names)


def _evaluate_list(data: Any, expected: list[str]) -> ExtractQuality:
    if not isinstance(data, list):
        return ExtractQuality(ok=False, status="empty", issues=["list result is not an array"])
    if not data:
        return ExtractQuality(ok=False, status="empty", issues=["empty list"], row_count=0, field_names=expected)

    dict_rows = [row for row in data if isinstance(row, Mapping)]
    if dict_rows:
        if len(dict_rows) != len(data):
            return ExtractQuality(
                ok=False,
                status="partial",
                issues=["list mixes object rows with scalar rows"],
                row_count=len(data),
                field_names=sorted({str(field) for row in dict_rows for field in row}),
            )
        return _evaluate_dict_rows(dict_rows, expected)

    issues: list[str] = []
    if all(_is_blank(row) for row in data):
        issues.append("all list items are blank")
    else:
        blank_count = sum(1 for row in data if _is_blank(row))
        if blank_count:
            issues.append(f"blank list items: {blank_count}/{len(data)}")
    return _finish(issues, row_count=len(data))


def _evaluate_table(data: Any, expected: list[str]) -> ExtractQuality:
    if not isinstance(data, list):
        return ExtractQuality(ok=False, status="empty", issues=["table result is not an array"])
    if not data:
        return ExtractQuality(ok=False, status="empty", issues=["empty table"], row_count=0, field_names=expected)
    if all(isinstance(row, Mapping) for row in data):
        return _evaluate_dict_rows(data, expected)

    rows = [row for row in data if isinstance(row, list)]
    if len(rows) != len(data):
        return ExtractQuality(ok=False, status="partial", issues=["table mixes row shapes"], row_count=len(data))
    if all(_is_blank(row) for row in rows):
        return ExtractQuality(ok=False, status="empty", issues=["all table rows are blank"], row_count=len(rows))

    blank_rows = sum(1 for row in rows if _is_blank(row))
    issues = [f"blank table rows: {blank_rows}/{len(rows)}"] if blank_rows else []
    field_names = [str(item) for item in rows[0]] if rows and not _is_blank(rows[0]) else expected
    return _finish(issues, row_count=len(rows), field_names=field_names)


def evaluate_extract_quality(
    extract_mode: str,
    data: Any,
    fields_map: Mapping[str, Any] | None = None,
) -> ExtractQuality:
    mode = str(extract_mode or "").strip().lower()
    expected = _expected_fields(fields_map)
    if mode == "text":
        return _evaluate_text(data)
    if mode == "attribute":
        return _evaluate_attribute(data, expected)
    if mode == "list":
        return _evaluate_list(data, expected)
    if mode == "table":
        return _evaluate_table(data, expected)
    return ExtractQuality(ok=False, status="partial", issues=[f"unknown extract mode: {extract_mode}"])
