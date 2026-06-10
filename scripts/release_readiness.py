#!/usr/bin/env python3
"""Summarize whether the next release is ready to cut."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from check_release_cadence import CadenceReport
from check_release_cadence import build_report as build_cadence_report
from validate_cases import CasesReport
from validate_cases import build_report as build_cases_report

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DraftReport:
    ok: bool
    path: str
    target_version: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "target_version": self.target_version,
            "issues": self.issues,
        }


@dataclass(frozen=True)
class CiReport:
    ok: bool
    path: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "issues": self.issues,
        }


@dataclass(frozen=True)
class PackageGateReport:
    ok: bool
    required: bool
    checked: bool
    packages_dir: str | None
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "required": self.required,
            "checked": self.checked,
            "packages_dir": self.packages_dir,
            "issues": self.issues,
        }


@dataclass(frozen=True)
class ReadinessReport:
    ok: bool
    current_version: str
    target_version: str
    blockers: list[str]
    cadence: CadenceReport
    cases: CasesReport
    draft: DraftReport
    ci: CiReport
    package_gate: PackageGateReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "blockers": self.blockers,
            "cadence": self.cadence.to_dict(),
            "cases": self.cases.to_dict(),
            "draft": self.draft.to_dict(),
            "ci": self.ci.to_dict(),
            "package_gate": self.package_gate.to_dict(),
        }


def _project_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _next_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        msg = f"Unsupported semantic version: {version}"
        raise ValueError(msg)
    major, minor, patch = parts
    return f"{major}.{minor}.{int(patch) + 1}"


def _draft_path(root: Path, target_version: str) -> Path:
    return root / "docs" / "releases" / f"v{target_version}-draft.md"


def _build_draft_report(root: Path, current_version: str, target_version: str) -> DraftReport:
    path = _draft_path(root, target_version)
    issues: list[str] = []
    if not path.exists():
        issues.append("release draft is missing")
        return DraftReport(ok=False, path=str(path), target_version=target_version, issues=issues)

    text = path.read_text(encoding="utf-8")
    required_snippets = [
        f"# v{target_version} 发布草案",
        f"**目标版本：** `{target_version}`",
        f"**提交范围：** `v{current_version}..HEAD`",
        "## 用户价值",
        "## 案例库映射",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            issues.append(f"release draft missing snippet: {snippet}")

    return DraftReport(ok=not issues, path=str(path), target_version=target_version, issues=issues)


def _build_ci_report(root: Path) -> CiReport:
    path = root / ".github" / "workflows" / "ci.yml"
    issues: list[str] = []
    if not path.exists():
        issues.append("CI workflow is missing")
        return CiReport(ok=False, path=str(path), issues=issues)

    text = path.read_text(encoding="utf-8")
    required_snippets = [
        "case-catalog:",
        "Case Catalog Validation",
        "python scripts/validate_cases.py --strict --report case-catalog-report.md",
        "pytest tests/test_validate_cases.py tests/test_cases_manifest.py -q --no-cov",
        "case-catalog-report",
        "case-catalog-report.md",
        "release-readiness:",
        "Release Readiness Report",
        "fetch-depth: 0",
        "python scripts/release_readiness.py --json --report release-readiness-report.md",
        "release-readiness-report",
        "release-readiness-report.md",
        "extract-quality:",
        "Extract Quality Regression",
        "CLIANY_QA_OFFLINE",
        "tests/test_extract_quality.py",
        "tests/test_extract_writer_quality.py",
        "tests/test_runtime_helpers_extract_quality.py",
        "tests/test_browser_part_c.py",
        "tests/test_generated_orchestration.py",
        "tests/test_search_extraction_gap_fixture.py",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            issues.append(f"CI workflow missing snippet: {snippet}")

    return CiReport(ok=not issues, path=str(path), issues=issues)


def _build_package_gate_report(
    *,
    packages_dir: Path | None,
    require_packages: bool,
    checked_packages: bool,
) -> PackageGateReport:
    issues: list[str] = []
    if require_packages and not checked_packages:
        issues.append("case package validation is required; pass --packages-dir")

    return PackageGateReport(
        ok=not issues,
        required=require_packages,
        checked=checked_packages,
        packages_dir=str(packages_dir) if packages_dir is not None else None,
        issues=issues,
    )


def _cadence_blockers(report: CadenceReport) -> list[str]:
    blockers: list[str] = []
    if report.commit_day_count < report.min_commit_days:
        blockers.append(f"commit days {report.commit_day_count}/{report.min_commit_days}")
    if not report.tag_matches_version:
        blockers.append(f"latest tag {report.latest_tag or '(none)'} != {report.expected_tag}")
    if not report.changelog_ok:
        blockers.append("CHANGELOG Unreleased has no content while HEAD is ahead of latest tag")
    if not report.changelog_unreleased_compare_ok:
        actual = report.changelog_unreleased_compare_actual or "(missing)"
        blockers.append(
            "CHANGELOG Unreleased compare link is stale: "
            f"{actual} != {report.changelog_unreleased_compare_expected}"
        )
    if report.dirty:
        blockers.append("working tree is dirty")
    return blockers


def build_report(
    root: Path = ROOT,
    *,
    today: date | None = None,
    min_commit_days: int = 3,
    target_version: str | None = None,
    packages_dir: Path | None = None,
    require_packages: bool = False,
) -> ReadinessReport:
    current_version = _project_version(root)
    expected_target = target_version or _next_patch_version(current_version)
    cadence = build_cadence_report(root, today=today or date.today(), min_commit_days=min_commit_days)
    cases = build_cases_report(root, packages_dir=packages_dir)
    draft = _build_draft_report(root, current_version, expected_target)
    ci = _build_ci_report(root)
    package_gate = _build_package_gate_report(
        packages_dir=packages_dir,
        require_packages=require_packages,
        checked_packages=cases.checked_packages,
    )

    blockers = _cadence_blockers(cadence)
    if not cases.ok:
        blockers.append("case catalog validation failed")
    if not draft.ok:
        blockers.append("release draft validation failed")
    if not ci.ok:
        blockers.append("CI release gates validation failed")
    if not package_gate.ok:
        blockers.append("case package validation not run")

    return ReadinessReport(
        ok=not blockers,
        current_version=current_version,
        target_version=expected_target,
        blockers=blockers,
        cadence=cadence,
        cases=cases,
        draft=draft,
        ci=ci,
        package_gate=package_gate,
    )


def _print_text(report: ReadinessReport) -> None:
    print("=== cliany-site release readiness ===")
    print(f"current_version: {report.current_version}")
    print(f"target_version: {report.target_version}")
    print(f"ok: {report.ok}")
    if report.blockers:
        print("blockers:")
        for blocker in report.blockers:
            print(f"- {blocker}")
    print(f"cadence: {report.cadence.ok}")
    print(f"cases: {report.cases.ok}")
    print(f"draft: {report.draft.ok}")
    print(f"ci: {report.ci.ok}")
    print(f"package_gate: {report.package_gate.ok}")


def _render_markdown_report(report: ReadinessReport) -> str:
    blockers = "<br>".join(report.blockers) if report.blockers else "-"
    commit_days = ", ".join(report.cadence.commit_days) if report.cadence.commit_days else "-"
    lines = [
        "# cliany-site Release Readiness",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| ok | `{str(report.ok).lower()}` |",
        f"| current_version | `{report.current_version}` |",
        f"| target_version | `{report.target_version}` |",
        f"| blockers | {blockers} |",
        "",
        "## Gates",
        "",
        "| Gate | Result | Detail |",
        "|------|--------|--------|",
        (
            f"| cadence | `{str(report.cadence.ok).lower()}` | "
            f"commit days `{report.cadence.commit_day_count}/{report.cadence.min_commit_days}`: {commit_days} |"
        ),
        f"| cases | `{str(report.cases.ok).lower()}` | active `{report.cases.active}` / total `{report.cases.total}` |",
        f"| draft | `{str(report.draft.ok).lower()}` | `{report.draft.path}` |",
        f"| ci | `{str(report.ci.ok).lower()}` | `{report.ci.path}` |",
        (
            f"| package_gate | `{str(report.package_gate.ok).lower()}` | "
            f"required `{str(report.package_gate.required).lower()}`, "
            f"checked `{str(report.package_gate.checked).lower()}` |"
        ),
        "",
        "## Release Links",
        "",
        f"- CHANGELOG compare: {report.cadence.changelog_unreleased_compare_actual or '(missing)'}",
        f"- Release draft: `{report.draft.path}`",
    ]
    return "\n".join(lines) + "\n"


def _write_markdown_report(report: ReadinessReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown_report(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check readiness for the next cliany-site release.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when release readiness fails.")
    parser.add_argument("--min-days", type=int, default=3, help="Minimum unique commit days expected this week.")
    parser.add_argument("--today", help="Override current date as YYYY-MM-DD, for tests or audits.")
    parser.add_argument("--target-version", help="Target release version. Defaults to next patch version.")
    parser.add_argument("--packages-dir", type=Path, help="Optional directory containing demo adapter packages.")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path for release review.")
    parser.add_argument(
        "--require-packages",
        action="store_true",
        help="Require --packages-dir package validation before reporting release readiness.",
    )
    args = parser.parse_args(argv)

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None
    report = build_report(
        ROOT,
        today=today,
        min_commit_days=args.min_days,
        target_version=args.target_version,
        packages_dir=args.packages_dir,
        require_packages=args.require_packages,
    )
    if args.report is not None:
        _write_markdown_report(report, args.report)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 1 if args.strict and not report.ok else 0


if __name__ == "__main__":
    sys.exit(main())
