#!/usr/bin/env python3
"""Validate the real-demo case catalog without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATUSES = {"active", "candidate", "degraded", "known-gap", "retired"}
INSTALL_RE = re.compile(r"^cliany-site market install (?P<path>\S+)")
REQUIRED_PACKAGE_FILES = {"commands.py", "metadata.json"}
BUILTIN_GROUPS = {
    "browser",
    "check",
    "doctor",
    "list",
    "login",
    "market",
    "migrate",
    "obscura",
    "replay",
    "report",
    "serve",
    "tui",
    "verify",
    "workflow",
}


@dataclass
class CaseCheck:
    id: str
    status: str
    issues: list[str] = field(default_factory=list)
    package: dict[str, Any] | None = None
    promotion: dict[str, Any] | None = None

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
        if self.promotion is not None:
            data["promotion"] = self.promotion
        return data


@dataclass
class CasesReport:
    ok: bool
    total: int
    active: int
    candidate: int
    known_gap: int
    checked_packages: bool
    cases: list[CaseCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total": self.total,
            "active": self.active,
            "candidate": self.candidate,
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


def _command_parts(command: Any) -> list[str]:
    try:
        return shlex.split(str(command))
    except ValueError:
        return str(command).split()


def _adapter_command_domains(commands: list[Any]) -> list[str]:
    domains: list[str] = []
    for command in commands:
        parts = _command_parts(command)
        if len(parts) < 2 or parts[0] != "cliany-site":
            continue
        group = parts[1]
        if group not in BUILTIN_GROUPS:
            domains.append(group)
    return domains


def _adapter_command_names(commands: list[Any]) -> set[str]:
    names: set[str] = set()
    for command in commands:
        parts = _command_parts(command)
        if len(parts) < 3 or parts[0] != "cliany-site":
            continue
        if parts[1] not in BUILTIN_GROUPS:
            names.add(parts[2])
    return names


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_member_names(tar: tarfile.TarFile) -> tuple[list[str], list[str]]:
    names = [member.name for member in tar.getmembers()]
    unsafe = [name for name in names if name.startswith("/") or ".." in Path(name).parts]
    return names, unsafe


def _github_heading_anchor(text: str) -> str:
    chars: list[str] = []
    for char in text.strip().lower():
        if char.isalnum() or char in {" ", "-"}:
            chars.append("-" if char.isspace() else char)
    return re.sub(r"-+", "-", "".join(chars)).strip("-")


def _markdown_heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = match.group(2).strip().strip("#").strip()
        anchor = _github_heading_anchor(heading)
        if not anchor:
            continue
        duplicate_count = counts.get(anchor, 0)
        counts[anchor] = duplicate_count + 1
        anchors.add(anchor if duplicate_count == 0 else f"{anchor}-{duplicate_count}")
    return anchors


def _validate_docs_link(root: Path, docs: str) -> list[str]:
    doc_path, _, raw_anchor = docs.partition("#")
    path = root / doc_path
    if not path.exists():
        return [f"docs path does not exist: {doc_path}"]
    if raw_anchor:
        anchor = unquote(raw_anchor).strip().lower()
        if anchor not in _markdown_heading_anchors(path):
            return [f"docs anchor does not exist: {docs}"]
    return []


def _validate_example_output(
    root: Path,
    case_id: str,
    example_output: str,
    expected_commands: set[str],
) -> list[str]:
    path = Path(example_output)
    if path.is_absolute() or ".." in path.parts:
        return [f"example_output path is unsafe: {example_output}"]
    if path.parts[:2] != ("cases", "examples"):
        return [f"example_output must be under cases/examples/: {example_output}"]

    full_path = root / path
    if not full_path.exists():
        return [f"example_output path does not exist: {example_output}"]

    try:
        payload = json.loads(full_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"example_output is not valid JSON: {exc}"]

    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["example_output must be a JSON object"]
    if payload.get("ok") is not True:
        issues.append("example_output.ok must be true")
    if payload.get("error") is not None:
        issues.append("example_output.error must be null")

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        issues.append("example_output.meta must be an object")
    else:
        if meta.get("case_id") != case_id:
            issues.append(f"example_output.meta.case_id must be {case_id!r}")
        if meta.get("sample") is not True:
            issues.append("example_output.meta.sample must be true")

    data = payload.get("data")
    if not isinstance(data, dict):
        issues.append("example_output.data must be an object")
    else:
        results = data.get("results")
        if not isinstance(results, list) or not results:
            issues.append("example_output.data.results must be a non-empty list")
        command_name = str(data.get("command") or "")
        if not command_name:
            issues.append("example_output.data.command is required")
        elif expected_commands and command_name not in expected_commands:
            expected = ", ".join(sorted(expected_commands))
            issues.append(
                f"example_output.data.command must match manifest commands: {command_name!r} not in {expected}"
            )

    return issues


def _extract_required_file(tar: tarfile.TarFile, name: str, issues: list[str]) -> bytes | None:
    try:
        extracted = tar.extractfile(name)
    except KeyError:
        extracted = None
    if extracted is None:
        issues.append(f"{name} missing")
        return None
    return extracted.read()


def _check_package(package_path: Path, expected_domain: str | None) -> dict[str, Any]:
    if not package_path.exists():
        return {
            "ok": False,
            "path": str(package_path),
            "status": "missing",
            "issue": "package file not found",
        }

    issues: list[str] = []
    try:
        with tarfile.open(package_path, "r:gz") as tar:
            member_names, unsafe_names = _safe_member_names(tar)
            if unsafe_names:
                issues.append(f"unsafe archive paths: {', '.join(unsafe_names)}")

            manifest_bytes = _extract_required_file(tar, "manifest.json", issues)
            manifest = json.loads(manifest_bytes.decode("utf-8")) if manifest_bytes else {}
            metadata_bytes = _extract_required_file(tar, "metadata.json", issues)
            _extract_required_file(tar, "commands.py", issues)

            payload_files = {name for name in member_names if name != "manifest.json"}
            manifest_files = {str(item) for item in manifest.get("files") or []}
            hash_files = {str(item) for item in (manifest.get("file_hashes") or {})}

            undeclared_files = sorted(payload_files - manifest_files)
            if undeclared_files:
                issues.append(f"undeclared package files: {', '.join(undeclared_files)}")

            missing_files = sorted(manifest_files - payload_files)
            if missing_files:
                issues.append(f"manifest.files missing from package: {', '.join(missing_files)}")

            missing_hashes = sorted(manifest_files - hash_files)
            if missing_hashes:
                issues.append(f"manifest.file_hashes missing: {', '.join(missing_hashes)}")

            unknown_hashes = sorted(hash_files - manifest_files)
            if unknown_hashes:
                issues.append(f"manifest.file_hashes has undeclared files: {', '.join(unknown_hashes)}")

            for filename in sorted(manifest_files & payload_files):
                if Path(filename).name != filename:
                    issues.append(f"unsafe manifest file name: {filename}")
                    continue
                expected_hash = str((manifest.get("file_hashes") or {}).get(filename, ""))
                if not expected_hash:
                    continue
                file_obj = tar.extractfile(filename)
                if file_obj is None:
                    continue
                actual_hash = _sha256_bytes(file_obj.read())
                if actual_hash != expected_hash:
                    issues.append(f"file hash mismatch: {filename}")

            if metadata_bytes:
                metadata = json.loads(metadata_bytes.decode("utf-8"))
                if metadata.get("schema_version") != 3:
                    issues.append("metadata.schema_version must be 3")
    except (OSError, tarfile.TarError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "ok": False,
            "path": str(package_path),
            "status": "invalid",
            "issue": str(exc),
        }

    if manifest.get("manifest_version") != "1":
        issues.append("manifest_version must be '1'")
    if expected_domain and manifest.get("domain") != expected_domain:
        issues.append(f"domain mismatch: expected {expected_domain!r}, got {manifest.get('domain')!r}")
    manifest_files = {str(item) for item in manifest.get("files") or []}
    if not manifest_files:
        issues.append("manifest.files is empty")
    missing_required = sorted(REQUIRED_PACKAGE_FILES - manifest_files)
    if missing_required:
        issues.append(f"manifest.files missing required files: {', '.join(missing_required)}")
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
        check.issues.extend(_validate_docs_link(root, docs))

    commands = case.get("commands") or []
    expected_commands = _adapter_command_names(commands)
    example_output = str(case.get("example_output") or "")
    if example_output:
        check.issues.extend(_validate_example_output(root, case_id, example_output, expected_commands))
    if status == "active":
        adapter_domain = str(case.get("adapter_domain") or "")
        if not adapter_domain:
            check.issues.append("active case requires adapter_domain")
        if not case.get("source_release"):
            check.issues.append("active case requires source_release")
        if not commands:
            check.issues.append("active case requires commands")
        if not example_output:
            check.issues.append("active case requires example_output")
        for command in commands:
            if not str(command).startswith("cliany-site "):
                check.issues.append(f"command must start with cliany-site: {command}")
        if adapter_domain:
            package_name = _install_package_name(case)
            if package_name and not package_name.startswith(f"{adapter_domain}."):
                check.issues.append(
                    f"install package domain mismatch: expected prefix {adapter_domain!r}, got {package_name!r}"
                )
            for command_domain in _adapter_command_domains(commands):
                if command_domain != adapter_domain:
                    check.issues.append(
                        f"adapter command domain mismatch: expected {adapter_domain!r}, got {command_domain!r}"
                    )
    elif status == "candidate":
        if not commands:
            check.issues.append("candidate case requires expected commands")
        if not example_output:
            check.issues.append("candidate case requires example_output")
        for command in commands:
            if not str(command).startswith("cliany-site "):
                check.issues.append(f"command must start with cliany-site: {command}")
        promotion = case.get("promotion")
        if not isinstance(promotion, dict):
            check.issues.append("candidate case requires promotion checklist")
        else:
            check.promotion = promotion
            for field_name in ("adapter_package", "metadata_validation", "online_smoke"):
                if not promotion.get(field_name):
                    check.issues.append(f"candidate promotion.{field_name} is required")

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
        candidate=sum(1 for case in cases if case.get("status") == "candidate"),
        known_gap=sum(1 for case in cases if case.get("status") == "known-gap"),
        checked_packages=packages_dir is not None,
        cases=checks,
    )


def _print_text(report: CasesReport) -> None:
    print("=== cliany-site cases validation ===")
    print(f"total: {report.total}")
    print(f"active: {report.active}")
    print(f"candidate: {report.candidate}")
    print(f"known_gap: {report.known_gap}")
    print(f"checked_packages: {report.checked_packages}")
    print(f"ok: {report.ok}")
    for check in report.cases:
        status = "ok" if check.ok else "fail"
        print(f"- {check.id}: {status} ({check.status})")
        for issue in check.issues:
            print(f"  issue: {issue}")
        if check.promotion is not None:
            print("  promotion:")
            for field_name in ("adapter_package", "metadata_validation", "online_smoke"):
                if check.promotion.get(field_name):
                    print(f"    {field_name}: {check.promotion[field_name]}")
        if check.package is not None and not check.package.get("ok"):
            print(f"  package: {check.package.get('status')} {check.package.get('issue', '')}".rstrip())
            for issue in check.package.get("issues", []):
                print(f"  package_issue: {issue}")


def _promotion_summary(promotion: dict[str, Any] | None) -> str:
    if promotion is None:
        return "-"
    parts = []
    for field_name in ("adapter_package", "metadata_validation", "online_smoke"):
        value = promotion.get(field_name)
        if value:
            parts.append(f"{field_name}: {value}")
    return "<br>".join(parts) if parts else "-"


def _render_markdown_report(report: CasesReport) -> str:
    lines = [
        "# cliany-site Case Catalog Validation",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| ok | `{str(report.ok).lower()}` |",
        f"| total | `{report.total}` |",
        f"| active | `{report.active}` |",
        f"| candidate | `{report.candidate}` |",
        f"| known_gap | `{report.known_gap}` |",
        f"| checked_packages | `{str(report.checked_packages).lower()}` |",
        "",
        "| Case | Status | Result | Issues | Package | Promotion |",
        "|------|--------|--------|--------|---------|-----------|",
    ]

    for check in report.cases:
        result = "ok" if check.ok else "fail"
        issues = "<br>".join(check.issues) if check.issues else "-"
        package = "-"
        if check.package is not None:
            package_status = str(check.package.get("status") or "unknown")
            package = package_status if check.package.get("ok") else f"fail: {package_status}"
        promotion = _promotion_summary(check.promotion)
        lines.append(f"| `{check.id}` | `{check.status}` | `{result}` | {issues} | {package} | {promotion} |")

    return "\n".join(lines) + "\n"


def _write_markdown_report(report: CasesReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown_report(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate cases/manifest.json and optional adapter packages.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when validation fails.")
    parser.add_argument("--packages-dir", type=Path, help="Optional directory containing .cliany-adapter.tar.gz files.")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path for CI artifacts.")
    args = parser.parse_args(argv)

    report = build_report(ROOT, packages_dir=args.packages_dir)
    if args.report is not None:
        _write_markdown_report(report, args.report)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 1 if args.strict and not report.ok else 0


if __name__ == "__main__":
    sys.exit(main())
