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
PACKAGE_EXTENSION = ".cliany-adapter.tar.gz"
PROMOTION_FIELDS = ("adapter_package", "metadata_validation", "online_smoke")
PROMOTION_EVIDENCE_STATUSES = {"pending", "complete", "blocked"}
BUILTIN_GROUPS = {
    "browser",
    "cases",
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
    target_url: str | None = None
    commands: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    package: dict[str, Any] | None = None
    promotion: dict[str, Any] | None = None
    promotion_evidence: dict[str, Any] | None = None
    offline_commands: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        package_ok = True if self.package is None else bool(self.package.get("ok"))
        return not self.issues and package_ok

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "status": self.status,
            "ok": self.ok,
            "target_url": self.target_url,
            "commands": self.commands,
            "issues": self.issues,
        }
        if self.package is not None:
            data["package"] = self.package
        if self.promotion is not None:
            data["promotion"] = self.promotion
        if self.promotion_evidence is not None:
            data["promotion_evidence"] = self.promotion_evidence
        if self.offline_commands:
            data["offline_commands"] = self.offline_commands
        return data


@dataclass
class CasesReport:
    ok: bool
    total: int
    active: int
    candidate: int
    known_gap: int
    checked_packages: bool
    promotion_evidence_summary: dict[str, Any]
    cases: list[CaseCheck]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total": self.total,
            "active": self.active,
            "candidate": self.candidate,
            "known_gap": self.known_gap,
            "checked_packages": self.checked_packages,
            "promotion_evidence_summary": self.promotion_evidence_summary,
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
        quality = data.get("quality")
        if not isinstance(quality, dict):
            issues.append("example_output.data.quality must be an object")
        else:
            if quality.get("ok") is not True:
                issues.append("example_output.data.quality.ok must be true")
            if quality.get("status") != "ok":
                issues.append("example_output.data.quality.status must be 'ok'")
            row_count = quality.get("row_count")
            if not isinstance(row_count, int) or row_count <= 0:
                issues.append("example_output.data.quality.row_count must be positive")

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


def _package_next_actions(issues: list[str]) -> list[str]:
    actions: list[str] = []
    for issue in issues:
        if issue.startswith("domain mismatch"):
            actions.append("Regenerate the package for the manifest adapter_domain or fix the case adapter_domain.")
        elif issue.startswith("metadata.schema_version"):
            actions.append("Regenerate the adapter metadata with schema_version 3.")
        elif issue.startswith("file hash mismatch") or "file_hashes" in issue:
            actions.append("Rebuild the adapter package so manifest.file_hashes match the packaged files.")
        elif "missing required files" in issue or issue.endswith("missing"):
            actions.append("Rebuild the adapter package with manifest.json, commands.py, and metadata.json.")
        elif issue.startswith("unsafe"):
            actions.append("Rebuild the adapter package without unsafe archive paths or nested manifest file names.")
        elif issue.startswith("undeclared package files") or issue.startswith("manifest.files missing from package"):
            actions.append("Align manifest.files with the files actually included in the package.")

    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def _check_package(package_path: Path, expected_domain: str | None) -> dict[str, Any]:
    if not package_path.exists():
        return {
            "ok": False,
            "path": str(package_path),
            "status": "missing",
            "issue": "package file not found",
            "next_actions": [
                f"Download or build the adapter package at {package_path}.",
                "Rerun python scripts/validate_cases.py --packages-dir <dir> --strict.",
            ],
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
            "next_actions": [
                "Regenerate the adapter package with cliany-site market publish.",
                "Confirm the tarball contains manifest.json, commands.py, and metadata.json.",
            ],
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
        "next_actions": _package_next_actions(issues),
    }


def _market_package_name_hint(domain: str) -> str:
    safe_domain = domain.replace("/", "_").replace(":", "_")
    return f"{safe_domain}-<version>{PACKAGE_EXTENSION}"


def _validate_candidate_promotion(promotion: dict[str, Any], adapter_domain: str) -> list[str]:
    issues: list[str] = []
    for field_name in PROMOTION_FIELDS:
        if not promotion.get(field_name):
            issues.append(f"candidate promotion.{field_name} is required")

    adapter_package = str(promotion.get("adapter_package") or "")
    if adapter_domain and adapter_package:
        expected_hint = _market_package_name_hint(adapter_domain)
        if f"{adapter_domain}.cliany-adapter-" in adapter_package:
            issues.append(f"candidate promotion.adapter_package uses legacy package naming; expected {expected_hint}")
        elif PACKAGE_EXTENSION in adapter_package and expected_hint not in adapter_package:
            issues.append(f"candidate promotion.adapter_package must use version placeholder: {expected_hint}")

    return issues


def _validate_candidate_promotion_evidence(evidence: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    unknown_tasks = sorted(str(task_name) for task_name in evidence if task_name not in PROMOTION_FIELDS)
    if unknown_tasks:
        issues.append(f"candidate promotion_evidence has unknown tasks: {', '.join(unknown_tasks)}")

    for task_name in PROMOTION_FIELDS:
        task = evidence.get(task_name)
        if not isinstance(task, dict):
            issues.append(f"candidate promotion_evidence.{task_name} is required")
            continue

        status = task.get("status")
        if status not in PROMOTION_EVIDENCE_STATUSES:
            allowed = ", ".join(sorted(PROMOTION_EVIDENCE_STATUSES))
            issues.append(f"candidate promotion_evidence.{task_name}.status must be one of: {allowed}")

        evidence_value = task.get("evidence")
        if evidence_value is not None and not isinstance(evidence_value, str):
            issues.append(f"candidate promotion_evidence.{task_name}.evidence must be a string or null")

        next_action = task.get("next_action")
        if next_action is not None and not isinstance(next_action, str):
            issues.append(f"candidate promotion_evidence.{task_name}.next_action must be a string or null")

        if status == "complete" and not evidence_value:
            issues.append(f"candidate promotion_evidence.{task_name}.evidence is required when status is complete")
        if status in {"pending", "blocked"} and not next_action:
            issues.append(f"candidate promotion_evidence.{task_name}.next_action is required when status is {status}")

    return issues


def _validate_offline_commands(validation: dict[str, Any]) -> tuple[list[str], list[str]]:
    commands = validation.get("offline_commands")
    if not isinstance(commands, list) or not commands:
        return [], ["validation.offline_commands is required"]

    issues: list[str] = []
    normalized: list[str] = []
    allowed_prefixes = (
        "python ",
        "pytest ",
        "CLIANY_QA_OFFLINE=1 ",
        "bash ",
    )
    for command in commands:
        if not isinstance(command, str) or not command.strip():
            issues.append("validation.offline_commands entries must be non-empty strings")
            continue
        command = command.strip()
        normalized.append(command)
        if not command.startswith(allowed_prefixes):
            issues.append(f"validation.offline_commands entry is not a local validation command: {command}")

    return normalized, issues


def _check_case(case: dict[str, Any], root: Path, packages_dir: Path | None) -> CaseCheck:
    case_id = str(case.get("id") or "(missing-id)")
    status = str(case.get("status") or "")
    target_url = str(case.get("target_url") or "")
    commands = [str(command) for command in case.get("commands") or []]
    check = CaseCheck(id=case_id, status=status, target_url=target_url or None, commands=commands)

    for field_name in ("id", "title", "category", "status", "target_url", "docs", "validation"):
        if not case.get(field_name):
            check.issues.append(f"missing required field: {field_name}")

    if status and status not in ALLOWED_STATUSES:
        check.issues.append(f"invalid status: {status}")

    if target_url and not target_url.startswith("https://"):
        check.issues.append("target_url must start with https://")

    validation = case.get("validation") or {}
    if not isinstance(validation, dict) or not validation.get("offline"):
        check.issues.append("validation.offline is required")
    if isinstance(validation, dict):
        check.offline_commands, offline_command_issues = _validate_offline_commands(validation)
        check.issues.extend(offline_command_issues)

    docs = str(case.get("docs") or "")
    if docs:
        check.issues.extend(_validate_docs_link(root, docs))

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
        adapter_domain = str(case.get("adapter_domain") or "")
        if not adapter_domain:
            check.issues.append("candidate case requires adapter_domain")
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
            check.issues.extend(_validate_candidate_promotion(promotion, adapter_domain))
        promotion_evidence = case.get("promotion_evidence")
        if not isinstance(promotion_evidence, dict):
            check.issues.append("candidate case requires promotion_evidence")
        else:
            check.promotion_evidence = promotion_evidence
            check.issues.extend(_validate_candidate_promotion_evidence(promotion_evidence))

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


def _build_promotion_evidence_summary(checks: list[CaseCheck]) -> dict[str, Any]:
    candidate_checks = [check for check in checks if check.status == "candidate"]
    status_counts = {status: 0 for status in sorted(PROMOTION_EVIDENCE_STATUSES)}
    task_status_counts = {
        field_name: {status: 0 for status in sorted(PROMOTION_EVIDENCE_STATUSES)}
        for field_name in PROMOTION_FIELDS
    }
    pending_tasks: list[dict[str, str]] = []
    blocked_tasks: list[dict[str, str]] = []
    complete_tasks: list[dict[str, str]] = []

    for check in candidate_checks:
        evidence = check.promotion_evidence or {}
        for field_name in PROMOTION_FIELDS:
            task = evidence.get(field_name)
            if not isinstance(task, dict):
                continue
            status = str(task.get("status") or "unknown")
            if status in status_counts:
                status_counts[status] += 1
                task_status_counts[field_name][status] += 1
            entry = {
                "case_id": check.id,
                "task": field_name,
                "status": status,
                "evidence": str(task.get("evidence") or ""),
                "next_action": str(task.get("next_action") or ""),
            }
            if status == "pending":
                pending_tasks.append(entry)
            elif status == "blocked":
                blocked_tasks.append(entry)
            elif status == "complete":
                complete_tasks.append(entry)

    primary = pending_tasks[0] if pending_tasks else (blocked_tasks[0] if blocked_tasks else None)
    return {
        "candidate_count": len(candidate_checks),
        "task_count": sum(status_counts.values()),
        "status_counts": status_counts,
        "task_status_counts": task_status_counts,
        "pending_count": len(pending_tasks),
        "blocked_count": len(blocked_tasks),
        "complete_count": len(complete_tasks),
        "pending_tasks": pending_tasks,
        "blocked_tasks": blocked_tasks,
        "complete_tasks": complete_tasks,
        "primary_task": primary,
        "primary_next_action": primary["next_action"] if primary else "",
    }


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
        promotion_evidence_summary=_build_promotion_evidence_summary(checks),
        cases=checks,
    )


def _print_text(report: CasesReport) -> None:
    print("=== cliany-site cases validation ===")
    print(f"total: {report.total}")
    print(f"active: {report.active}")
    print(f"candidate: {report.candidate}")
    print(f"known_gap: {report.known_gap}")
    print(f"checked_packages: {report.checked_packages}")
    print(f"promotion_evidence_pending: {report.promotion_evidence_summary['pending_count']}")
    print(f"promotion_evidence_blocked: {report.promotion_evidence_summary['blocked_count']}")
    print(f"promotion_evidence_complete: {report.promotion_evidence_summary['complete_count']}")
    if report.promotion_evidence_summary["primary_next_action"]:
        print(f"promotion_evidence_next: {report.promotion_evidence_summary['primary_next_action']}")
    print(f"ok: {report.ok}")
    for check in report.cases:
        status = "ok" if check.ok else "fail"
        print(f"- {check.id}: {status} ({check.status})")
        for issue in check.issues:
            print(f"  issue: {issue}")
        if check.promotion is not None:
            print("  promotion:")
            for field_name in PROMOTION_FIELDS:
                if check.promotion.get(field_name):
                    print(f"    {field_name}: {check.promotion[field_name]}")
        if check.promotion_evidence is not None:
            print("  promotion_evidence:")
            for field_name in PROMOTION_FIELDS:
                task = check.promotion_evidence.get(field_name)
                if isinstance(task, dict):
                    print(f"    {field_name}: {task.get('status')}")
        if check.package is not None and not check.package.get("ok"):
            print(f"  package: {check.package.get('status')} {check.package.get('issue', '')}".rstrip())
            for issue in check.package.get("issues", []):
                print(f"  package_issue: {issue}")


def _promotion_summary(promotion: dict[str, Any] | None) -> str:
    if promotion is None:
        return "-"
    parts = []
    for field_name in PROMOTION_FIELDS:
        value = promotion.get(field_name)
        if value:
            parts.append(f"{field_name}: {value}")
    return "<br>".join(parts) if parts else "-"


def _promotion_evidence_summary(evidence: dict[str, Any] | None) -> str:
    if evidence is None:
        return "-"
    parts = []
    for field_name in PROMOTION_FIELDS:
        task = evidence.get(field_name)
        if not isinstance(task, dict):
            continue
        status = str(task.get("status") or "unknown")
        next_action = task.get("next_action")
        evidence_value = task.get("evidence")
        details = [f"{field_name}: {status}"]
        if evidence_value:
            details.append(f"evidence: {evidence_value}")
        if next_action:
            details.append(f"next: {next_action}")
        parts.append("; ".join(details))
    return "<br>".join(parts) if parts else "-"


def _offline_command_summary(commands: list[str]) -> str:
    return "<br>".join(commands) if commands else "-"


def _command_summary(commands: list[str]) -> str:
    return "<br>".join(commands) if commands else "-"


def _package_summary(package: dict[str, Any] | None) -> str:
    if package is None:
        return "-"
    package_status = str(package.get("status") or "unknown")
    if package.get("ok"):
        return package_status

    parts = [f"fail: {package_status}"]
    if package.get("issue"):
        parts.append(str(package["issue"]))
    issues = [str(issue) for issue in package.get("issues") or []]
    parts.extend(issues)
    next_actions = [str(action) for action in package.get("next_actions") or []]
    parts.extend(f"next: {action}" for action in next_actions)
    return "<br>".join(parts)


def _candidate_promotion_evidence_summary_lines(summary: dict[str, Any]) -> list[str]:
    lines = [
        "",
        "## Candidate Promotion Evidence Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| candidate_count | `{summary.get('candidate_count', 0)}` |",
        f"| task_count | `{summary.get('task_count', 0)}` |",
        f"| pending_count | `{summary.get('pending_count', 0)}` |",
        f"| blocked_count | `{summary.get('blocked_count', 0)}` |",
        f"| complete_count | `{summary.get('complete_count', 0)}` |",
        f"| primary_next_action | {_markdown_cell(summary.get('primary_next_action') or '-')} |",
        "",
        "| Case | Task | Status | Evidence | Next Action |",
        "|------|------|--------|----------|-------------|",
    ]
    task_rows = [
        *list(summary.get("pending_tasks") or []),
        *list(summary.get("blocked_tasks") or []),
        *list(summary.get("complete_tasks") or []),
    ]
    if not task_rows:
        lines.append("| - | - | - | - | - |")
        return lines
    for task in task_rows:
        lines.append(
            "| "
            f"`{_markdown_cell(task.get('case_id'))}` | "
            f"`{_markdown_cell(task.get('task'))}` | "
            f"`{_markdown_cell(task.get('status'))}` | "
            f"{_markdown_cell(task.get('evidence') or '-')} | "
            f"{_markdown_cell(task.get('next_action') or '-')} |"
        )
    return lines


def _markdown_cell(value: object) -> str:
    return str(value or "-").replace("|", "\\|").replace("\n", "<br>")


def _candidate_promotion_task_lines(report: CasesReport) -> list[str]:
    candidates = [case for case in report.cases if case.status == "candidate" and case.promotion]
    if not candidates:
        return []

    lines = [
        "",
        "## Candidate Promotion Tasks",
        "",
        "Use these issue-ready tasks to move candidate cases toward active status without bundling "
        "package creation, metadata validation, and online smoke evidence into one PR. "
        "Each task includes the current structured evidence status from `promotion_evidence`.",
    ]
    for case in candidates:
        promotion = case.promotion or {}
        evidence = case.promotion_evidence or {}
        command_lines = [f"  - `{command}`" for command in case.commands] or ["  - Not declared."]
        offline_command_lines = [
            f"  - `{command}`" for command in case.offline_commands
        ] or ["  - Not declared."]
        task_lines: list[str] = []
        issue_task_lines: list[str] = []
        for field_name in PROMOTION_FIELDS:
            task = evidence.get(field_name) if isinstance(evidence, dict) else {}
            task = task if isinstance(task, dict) else {}
            status = task.get("status") or "unknown"
            next_action = task.get("next_action") or "Not declared."
            evidence_value = task.get("evidence") or "Not attached yet."
            task_lines.extend(
                [
                    f"- [ ] `{field_name}`: {promotion.get(field_name)}",
                    f"  - Status: `{status}`",
                    f"  - Evidence: {evidence_value}",
                    f"  - Next action: {next_action}",
                ]
            )
            issue_task_lines.extend(
                [
                    f"- [ ] `{field_name}`: {promotion.get(field_name)}",
                    f"  - Current status: `{status}`",
                    f"  - Current evidence: {evidence_value}",
                    f"  - Next action: {next_action}",
                ]
            )
        lines.extend(
            [
                "",
                f"### `{case.id}`",
                "",
                *task_lines,
                "",
                "#### Issue Body Template",
                "",
                "```markdown",
                f"## Scope: promote candidate case `{case.id}`",
                "",
                "Move this candidate case one step closer to `active` without changing its status early.",
                "",
                "## Reproduction Context",
                f"- Target URL: {case.target_url or 'Not declared.'}",
                "- Candidate commands:",
                *command_lines,
                "- Offline validation commands:",
                *offline_command_lines,
                "",
                "## Tasks",
                *issue_task_lines,
                "",
                "## Evidence Bundle",
                f"- Human: `cliany-site cases --case-id {case.id} --evidence-bundle`",
                f"- JSON: `cliany-site cases --case-id {case.id} --evidence-bundle --json`",
                "- Attach or paste the JSON output in the issue once evidence changes.",
                "",
                "## Validation Evidence",
                "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.",
                "- Paste the local `scripts/validate_cases.py --packages-dir` result.",
                "- Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`.",
                "",
                "## Non-goals",
                "- Do not mark the case `active` until all three promotion tasks are complete.",
                "- Do not require real LLM keys or write runtime state into the repository.",
                "```",
            ]
        )
    return lines


def _candidate_handoff_lines(report: CasesReport) -> list[str]:
    candidates = [case for case in report.cases if case.status == "candidate"]
    if not candidates:
        return []
    lines = [
        "",
        "## Candidate Handoff Matrix",
        "",
        "Use this matrix to turn candidate cases into focused contributor tasks without reopening "
        "`cases/manifest.json` for the basic reproduction context.",
        "",
        "| Case | Target URL | Commands | Offline Validation |",
        "|------|------------|----------|--------------------|",
    ]
    for case in candidates:
        lines.append(
            f"| `{case.id}` | {case.target_url or '-'} | {_command_summary(case.commands)} | "
            f"{_offline_command_summary(case.offline_commands)} |"
        )
    return lines


def _candidate_evidence_bundle_command_lines(report: CasesReport) -> list[str]:
    candidates = [case for case in report.cases if case.status == "candidate"]
    if not candidates:
        return []
    lines = [
        "",
        "## Candidate Evidence Bundle Commands",
        "",
        "Use these commands to print a local evidence checklist for each candidate case before opening "
        "or updating a promotion issue.",
        "",
        "| Case | Human Handoff | JSON Evidence |",
        "|------|---------------|---------------|",
    ]
    for case in candidates:
        human_command = f"cliany-site cases --case-id {case.id} --evidence-bundle"
        json_command = f"cliany-site cases --case-id {case.id} --evidence-bundle --json"
        lines.append(
            f"| `{case.id}` | `{_markdown_cell(human_command)}` | `{_markdown_cell(json_command)}` |"
        )
    return lines


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
        "| Case | Status | Result | Issues | Package | Promotion | Promotion Evidence |",
        "|------|--------|--------|--------|---------|-----------|--------------------|",
    ]

    for check in report.cases:
        result = "ok" if check.ok else "fail"
        issues = _markdown_cell("<br>".join(check.issues) if check.issues else "-")
        package = _package_summary(check.package)
        promotion = _promotion_summary(check.promotion)
        promotion_evidence = _promotion_evidence_summary(check.promotion_evidence)
        lines.append(
            f"| `{check.id}` | `{check.status}` | `{result}` | {issues} | "
            f"{package} | {promotion} | {promotion_evidence} |"
        )

    lines.extend(
        [
            "",
            "## Offline Validation Commands",
            "",
            "| Case | Commands |",
            "|------|----------|",
        ]
    )
    for check in report.cases:
        lines.append(f"| `{check.id}` | {_offline_command_summary(check.offline_commands)} |")

    lines.extend(_candidate_handoff_lines(report))
    lines.extend(_candidate_evidence_bundle_command_lines(report))
    lines.extend(_candidate_promotion_evidence_summary_lines(report.promotion_evidence_summary))
    lines.extend(_candidate_promotion_task_lines(report))
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
