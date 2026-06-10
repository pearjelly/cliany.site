#!/usr/bin/env python3
"""Validate the real-demo case catalog without network access."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"active", "degraded", "known-gap", "retired"}
INSTALL_RE = re.compile(r"^cliany-site market install (?P<path>\S+)")


@dataclass
class CaseCheck:
    id: str
    status: str
    issues: list[str] = field(default_factory=list)
    package: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        package_ok = True if self.package is None else bool(self.package.get("ok"))
        return not self.issues and package_ok

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "status": self.status,
            "ok": self.ok,
            "issues": self.issues,
        }
        if self.package is not None:
            data["package"] = self.package
        return data


@dataclass
class CasesReport:
    ok: bool
    total: int
    active: int
    known_gap: int
    checked_packages: bool
    cases: list[CaseCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total": self.total,
            "active": self.active,
            "known_gap": self.known_gap,
            "checked_packages": self.checked_packages,
            "cases": [case.to_dict() for case in self.cases],
        }


def _load_manifest(root: Path) -> list[dict[str, Any]]:
    data = json.loads((root / "cases" / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(data, list):
        msg = "cases/manifest.json must be a JSON array"
        raise ValueError(msg)
    return data


def _install_package_name(case: dict[str, Any]) -> str | None:
    for command in case.get("commands") or []:
        match = INSTALL_RE.match(str(command))
        if match:
            return Path(match.group("path")).name
    return None


def _check_package(package_path: Path, expected_domain: str | None) -> dict[str, Any]:
    if not package_path.exists():
        return {
            "ok": False,
            "path": str(package_path),
            "status": "missing",
            "issue": "package file not found",
        }

    try:
        with tarfile.open(package_path, "r:gz") as tar:
            manifest_file = tar.extractfile("manifest.json")
            if manifest_file is None:
                return {
                    "ok": False,
                    "path": str(package_path),
                    "status": "invalid",
                    "issue": "manifest.json missing",
                }
            manifest = json.loads(manifest_file.read().decode("utf-8"))
    except (OSError, tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "ok": False,
            "path": str(package_path),
            "status": "invalid",
            "issue": str(exc),
        }

    issues: list[str] = []
    if manifest.get("manifest_version") != "1":
        issues.append("manifest_version must be '1'")
    if expected_domain and manifest.get("domain") != expected_domain:
        issues.append(f"domain mismatch: expected {expected_domain!r}, got {manifest.get('domain')!r}")
    if not manifest.get("files"):
        issues.append("manifest.files is empty")
    if not manifest.get("file_hashes"):
        issues.append("manifest.file_hashes is empty")

    return {
        "ok": not issues,
        "path": str(package_path),
        "status": "ok" if not issues else "invalid",
        "issues": issues,
    }


def _check_case(case: dict[str, Any], root: Path, packages_dir: Path | None) -> CaseCheck:
    case_id = str(case.get("id") or "(missing-id)")
    status = str(case.get("status") or "")
    check = CaseCheck(id=case_id, status=status)

    for field_name in ("id", "title", "category", "status", "target_url", "docs", "validation"):
        if not case.get(field_name):
            check.issues.append(f"missing required field: {field_name}")

    if status and status not in ALLOWED_STATUSES:
        check.issues.append(f"invalid status: {status}")

    target_url = str(case.get("target_url") or "")
    if target_url and not target_url.startswith("https://"):
        check.issues.append("target_url must start with https://")

    validation = case.get("validation") or {}
    if not isinstance(validation, dict) or not validation.get("offline"):
        check.issues.append("validation.offline is required")

    docs = str(case.get("docs") or "")
    if docs:
        doc_path = docs.split("#", 1)[0]
        if not (root / doc_path).exists():
            check.issues.append(f"docs path does not exist: {doc_path}")

    commands = case.get("commands") or []
    if status == "active":
        if not case.get("adapter_domain"):
            check.issues.append("active case requires adapter_domain")
        if not case.get("source_release"):
            check.issues.append("active case requires source_release")
        if not commands:
            check.issues.append("active case requires commands")
        for command in commands:
            if not str(command).startswith("cliany-site "):
                check.issues.append(f"command must start with cliany-site: {command}")

    if packages_dir is not None and status == "active":
        package_name = _install_package_name(case)
        if package_name is None:
            check.package = {
                "ok": False,
                "status": "missing-install-command",
                "issue": "active case has no market install command",
            }
        else:
            check.package = _check_package(packages_dir / package_name, case.get("adapter_domain"))

    return check


def build_report(root: Path = ROOT, packages_dir: Path | None = None) -> CasesReport:
    cases = _load_manifest(root)
    checks = [_check_case(case, root, packages_dir) for case in cases]
    ids = [str(case.get("id") or "") for case in cases]
    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicate_ids:
        for check in checks:
            if check.id in duplicate_ids:
                check.issues.append("duplicate case id")

    return CasesReport(
        ok=all(check.ok for check in checks),
        total=len(checks),
        active=sum(1 for case in cases if case.get("status") == "active"),
        known_gap=sum(1 for case in cases if case.get("status") == "known-gap"),
        checked_packages=packages_dir is not None,
        cases=checks,
    )


def _print_text(report: CasesReport) -> None:
    print("=== cliany-site cases validation ===")
    print(f"total: {report.total}")
    print(f"active: {report.active}")
    print(f"known_gap: {report.known_gap}")
    print(f"checked_packages: {report.checked_packages}")
    print(f"ok: {report.ok}")
    for check in report.cases:
        status = "ok" if check.ok else "fail"
        print(f"- {check.id}: {status} ({check.status})")
        for issue in check.issues:
            print(f"  issue: {issue}")
        if check.package is not None and not check.package.get("ok"):
            print(f"  package: {check.package.get('status')} {check.package.get('issue', '')}".rstrip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate cases/manifest.json and optional adapter packages.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when validation fails.")
    parser.add_argument("--packages-dir", type=Path, help="Optional directory containing .cliany-adapter.tar.gz files.")
    args = parser.parse_args(argv)

    report = build_report(ROOT, packages_dir=args.packages_dir)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 1 if args.strict and not report.ok else 0


if __name__ == "__main__":
    sys.exit(main())
