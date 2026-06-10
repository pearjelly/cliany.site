#!/usr/bin/env python3
"""Check weekly release cadence without network or service credentials."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CadenceReport:
    ok: bool
    version: str
    latest_tag: str | None
    expected_tag: str
    tag_matches_version: bool
    commit_days: list[str]
    commit_day_count: int
    min_commit_days: int
    commits_since_latest_tag: int | None
    changelog_unreleased_has_content: bool
    changelog_unreleased_compare_ok: bool
    changelog_unreleased_compare_expected: str
    changelog_unreleased_compare_actual: str | None
    changelog_ok: bool
    dirty: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "version": self.version,
            "latest_tag": self.latest_tag,
            "expected_tag": self.expected_tag,
            "tag_matches_version": self.tag_matches_version,
            "commit_days": self.commit_days,
            "commit_day_count": self.commit_day_count,
            "min_commit_days": self.min_commit_days,
            "commits_since_latest_tag": self.commits_since_latest_tag,
            "changelog_unreleased_has_content": self.changelog_unreleased_has_content,
            "changelog_unreleased_compare_ok": self.changelog_unreleased_compare_ok,
            "changelog_unreleased_compare_expected": self.changelog_unreleased_compare_expected,
            "changelog_unreleased_compare_actual": self.changelog_unreleased_compare_actual,
            "changelog_ok": self.changelog_ok,
            "dirty": self.dirty,
        }


def _run_git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def _optional_git(args: list[str], cwd: Path) -> str | None:
    try:
        return _run_git(args, cwd)
    except subprocess.CalledProcessError:
        return None


def _week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def _project_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _latest_tag(root: Path) -> str | None:
    return _optional_git(["describe", "--tags", "--abbrev=0"], root)


def _commit_days_since(root: Path, start: date) -> list[str]:
    output = _optional_git(
        ["log", f"--since={start.isoformat()} 00:00:00", "--date=short", "--pretty=format:%ad"],
        root,
    )
    if not output:
        return []
    return sorted(set(line.strip() for line in output.splitlines() if line.strip()))


def _commits_since_tag(root: Path, tag: str | None) -> int | None:
    if tag is None:
        return None
    output = _optional_git(["rev-list", "--count", f"{tag}..HEAD"], root)
    return int(output) if output is not None else None


def _changelog_unreleased_has_content(root: Path) -> bool:
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    marker = "## [Unreleased]"
    start = changelog.find(marker)
    if start == -1:
        return False
    next_release = changelog.find("\n## [", start + len(marker))
    section = changelog[start + len(marker): next_release if next_release != -1 else len(changelog)]
    meaningful_lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("###")
    ]
    return bool(meaningful_lines)


def _changelog_unreleased_compare_link(
    root: Path,
    latest_tag: str | None,
    expected_tag: str,
) -> tuple[bool, str, str | None]:
    expected_base = latest_tag or expected_tag
    expected = f"https://github.com/pearjelly/cliany.site/compare/{expected_base}...HEAD"
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^\[Unreleased\]:\s*(\S+)\s*$", changelog, flags=re.MULTILINE)
    actual = match.group(1) if match else None
    return actual == expected, expected, actual


def _is_dirty(root: Path) -> bool:
    status = _optional_git(["status", "--short"], root)
    return bool(status)


def build_report(root: Path, today: date, min_commit_days: int) -> CadenceReport:
    version = _project_version(root)
    latest_tag = _latest_tag(root)
    expected_tag = f"v{version}"
    commit_days = _commit_days_since(root, _week_start(today))
    changelog_has_content = _changelog_unreleased_has_content(root)
    dirty = _is_dirty(root)
    commits_since_latest_tag = _commits_since_tag(root, latest_tag)
    tag_matches_version = latest_tag == expected_tag
    compare_ok, compare_expected, compare_actual = _changelog_unreleased_compare_link(root, latest_tag, expected_tag)
    changelog_ok = changelog_has_content or commits_since_latest_tag == 0
    ok = (
        len(commit_days) >= min_commit_days
        and tag_matches_version
        and changelog_ok
        and compare_ok
        and not dirty
    )
    return CadenceReport(
        ok=ok,
        version=version,
        latest_tag=latest_tag,
        expected_tag=expected_tag,
        tag_matches_version=tag_matches_version,
        commit_days=commit_days,
        commit_day_count=len(commit_days),
        min_commit_days=min_commit_days,
        commits_since_latest_tag=commits_since_latest_tag,
        changelog_unreleased_has_content=changelog_has_content,
        changelog_unreleased_compare_ok=compare_ok,
        changelog_unreleased_compare_expected=compare_expected,
        changelog_unreleased_compare_actual=compare_actual,
        changelog_ok=changelog_ok,
        dirty=dirty,
    )


def _print_text(report: CadenceReport) -> None:
    print("=== cliany-site release cadence ===")
    print(f"version: {report.version}")
    print(f"latest_tag: {report.latest_tag or '(none)'}")
    print(f"expected_tag: {report.expected_tag}")
    print(f"tag_matches_version: {report.tag_matches_version}")
    print(f"commit_days: {report.commit_day_count}/{report.min_commit_days} {', '.join(report.commit_days)}")
    print(f"commits_since_latest_tag: {report.commits_since_latest_tag}")
    print(f"changelog_unreleased_has_content: {report.changelog_unreleased_has_content}")
    print(f"changelog_unreleased_compare_ok: {report.changelog_unreleased_compare_ok}")
    print(f"changelog_unreleased_compare_expected: {report.changelog_unreleased_compare_expected}")
    print(f"changelog_unreleased_compare_actual: {report.changelog_unreleased_compare_actual or '(missing)'}")
    print(f"changelog_ok: {report.changelog_ok}")
    print(f"dirty: {report.dirty}")
    print(f"ok: {report.ok}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check weekly release and commit cadence.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when cadence checks are not satisfied.")
    parser.add_argument("--min-days", type=int, default=3, help="Minimum unique commit days expected this week.")
    parser.add_argument("--today", help="Override current date as YYYY-MM-DD, for tests or audits.")
    args = parser.parse_args(argv)

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else date.today()
    report = build_report(ROOT, today=today, min_commit_days=args.min_days)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 1 if args.strict and not report.ok else 0


if __name__ == "__main__":
    sys.exit(main())
