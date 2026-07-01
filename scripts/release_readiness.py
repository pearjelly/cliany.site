#!/usr/bin/env python3
"""Summarize whether the next release is ready to cut."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from check_release_cadence import CadenceReport
from check_release_cadence import build_report as build_cadence_report
from check_release_publication import PublicationReport
from check_release_publication import build_report as build_publication_report
from validate_cases import CasesReport
from validate_cases import build_report as build_cases_report

ROOT = Path(__file__).resolve().parents[1]
MIN_CASE_ASSETS = 8
RELEASE_PREFLIGHT_COMMAND = (
    "python scripts/release_readiness.py --strict "
    '--release-tag "${{ github.ref_name }}" '
    "--report release-readiness-report.md"
)
NODE24_ACTIONS_ENV_SNIPPET = 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"'
PROMOTION_FIELDS = ("adapter_package", "metadata_validation", "online_smoke")


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
class ReleaseWorkflowReport:
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
class ProjectMetadataReport:
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
    failed_count: int
    missing_count: int
    invalid_count: int
    repair_action_count: int
    primary_repair_action: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "required": self.required,
            "checked": self.checked,
            "packages_dir": self.packages_dir,
            "issues": self.issues,
            "failed_count": self.failed_count,
            "missing_count": self.missing_count,
            "invalid_count": self.invalid_count,
            "repair_action_count": self.repair_action_count,
            "primary_repair_action": self.primary_repair_action,
        }


@dataclass(frozen=True)
class ReadinessReport:
    ok: bool
    current_version: str
    target_version: str
    release_mode: str
    release_tag: str | None
    blockers: list[str]
    min_case_assets: int
    cadence: CadenceReport
    cases: CasesReport
    draft: DraftReport
    ci: CiReport
    release_workflow: ReleaseWorkflowReport
    project_metadata: ProjectMetadataReport
    package_gate: PackageGateReport
    publication: PublicationReport
    remote_check: bool = False
    remote_name: str = "origin"

    def to_dict(self) -> dict[str, Any]:
        publication_payload = _publication_payload(self)
        publication_ref_context = _publication_ref_context(publication_payload)
        publication_blockers = _publication_blockers(self.publication)
        publication_next_actions = publication_payload["next_actions"]
        publication_publish_commands = publication_payload["publish_commands"]
        publication_summary = _publication_summary(publication_payload)
        primary_runbook = _case_promotion_primary_runbook(self.cases)
        primary_runbook_steps = _runbook_steps(primary_runbook)
        next_actions = _next_action_lines(self)
        standard_release_flow = _standard_release_flow(
            self,
            publication_payload=publication_payload,
            next_actions=next_actions,
        )
        return {
            "ok": self.ok,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "release_mode": self.release_mode,
            "release_tag": self.release_tag,
            "blockers": self.blockers,
            "min_case_assets": self.min_case_assets,
            "cadence": self.cadence.to_dict(),
            "cases": self.cases.to_dict(),
            "case_promotion_evidence_primary_runbook": primary_runbook,
            "case_promotion_evidence_primary_runbook_step_count": len(primary_runbook_steps),
            "case_promotion_evidence_primary_runbook_steps": primary_runbook_steps,
            "case_promotion_evidence_primary_runbook_steps_sha256": _stable_json_sha256(
                primary_runbook_steps
            ),
            "draft": self.draft.to_dict(),
            "ci": self.ci.to_dict(),
            "release_workflow": self.release_workflow.to_dict(),
            "project_metadata": self.project_metadata.to_dict(),
            "package_gate": self.package_gate.to_dict(),
            "publication": publication_payload,
            "publication_ok": publication_payload["ok"],
            "publication_summary": publication_summary,
            "publication_summary_sha256": _stable_json_sha256(publication_summary),
            "publication_summary_primary_next_action": publication_summary["primary_next_action"],
            "publication_summary_primary_publish_command": publication_summary["primary_publish_command"],
            "publication_ref_context": publication_ref_context,
            "publication_worktree_clean": publication_payload["worktree_clean"],
            "publication_worktree_status_count": len(publication_payload["worktree_status"]),
            "publication_worktree_status": publication_payload["worktree_status"],
            "publication_tag_publish_decision": publication_payload["tag_publish_decision"],
            "publication_blocker_count": len(publication_blockers),
            "publication_blockers_sha256": _stable_json_sha256(publication_blockers),
            "publication_primary_blocker": publication_blockers[0] if publication_blockers else None,
            "publication_blockers": publication_blockers,
            "publication_next_action_count": publication_payload["next_action_count"],
            "publication_next_actions_sha256": _stable_json_sha256(publication_next_actions),
            "publication_primary_next_action": publication_next_actions[0] if publication_next_actions else None,
            "publication_next_actions": publication_next_actions,
            "publication_publish_command_count": publication_payload["publish_command_count"],
            "publication_publish_commands_sha256": _stable_json_sha256(
                publication_publish_commands
            ),
            "publication_primary_publish_command": (
                publication_publish_commands[0] if publication_publish_commands else None
            ),
            "publication_publish_commands": publication_publish_commands,
            "standard_release_flow": standard_release_flow,
            "standard_release_flow_status": standard_release_flow["status"],
            "standard_release_flow_primary_next_action": standard_release_flow[
                "primary_next_action"
            ],
            "standard_release_flow_command_count": standard_release_flow["command_count"],
            "standard_release_flow_commands_sha256": standard_release_flow[
                "commands_sha256"
            ],
            "standard_release_flow_sha256": _stable_json_sha256(standard_release_flow),
            "next_action_count": len(next_actions),
            "next_actions_sha256": _stable_json_sha256(next_actions),
            "primary_next_action": next_actions[0] if next_actions else None,
            "next_actions": next_actions,
        }


def _project_version(root: Path) -> str:
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _optional_git(args: list[str], cwd: Path) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return None


def _next_patch_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3:
        msg = f"Unsupported semantic version: {version}"
        raise ValueError(msg)
    major, minor, patch = parts
    return f"{major}.{minor}.{int(patch) + 1}"


def _strip_v_prefix(version_or_tag: str) -> str:
    return version_or_tag[1:] if version_or_tag.startswith("v") else version_or_tag


def _previous_tag_version(root: Path, release_tag: str) -> str | None:
    previous_tag = _optional_git(["describe", "--tags", "--abbrev=0", f"{release_tag}^"], root)
    return _strip_v_prefix(previous_tag) if previous_tag else None


def _tag_points_at_head(root: Path, release_tag: str) -> bool:
    tag_commit = _optional_git(["rev-list", "-n", "1", release_tag], root)
    head_commit = _optional_git(["rev-parse", "HEAD"], root)
    return bool(tag_commit and head_commit and tag_commit == head_commit)


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
        NODE24_ACTIONS_ENV_SNIPPET,
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


def _build_release_workflow_report(root: Path) -> ReleaseWorkflowReport:
    path = root / ".github" / "workflows" / "release.yml"
    issues: list[str] = []
    if not path.exists():
        issues.append("release workflow is missing")
        return ReleaseWorkflowReport(ok=False, path=str(path), issues=issues)

    text = path.read_text(encoding="utf-8")
    required_snippets = [
        'tags: ["v*"]',
        "contents: write",
        "id-token: write",
        NODE24_ACTIONS_ENV_SNIPPET,
        "release-preflight:",
        "Release Preflight",
        "fetch-depth: 0",
        RELEASE_PREFLIGHT_COMMAND,
        "release-readiness-report",
        "needs: release-preflight",
        "Build Distribution",
        "rm -rf dist",
        "uv build",
        "uvx twine check dist/*",
        "actions/upload-artifact@v4",
        "GitHub Release",
        "gh release create",
        "Publish to PyPI",
        "name: pypi",
        "https://pypi.org/p/cliany-site",
        "pypa/gh-action-pypi-publish@release/v1",
    ]
    for snippet in required_snippets:
        if snippet not in text:
            issues.append(f"release workflow missing snippet: {snippet}")

    return ReleaseWorkflowReport(ok=not issues, path=str(path), issues=issues)


def _build_project_metadata_report(root: Path) -> ProjectMetadataReport:
    path = root / "pyproject.toml"
    issues: list[str] = []
    if not path.exists():
        issues.append("pyproject.toml is missing")
        return ProjectMetadataReport(ok=False, path=str(path), issues=issues)

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    if not project.get("description"):
        issues.append("project.description is required for PyPI")
    readme = project.get("readme")
    if not readme:
        issues.append("project.readme is required for PyPI long description")
    elif isinstance(readme, str) and not (root / readme).exists():
        issues.append(f"project.readme does not exist: {readme}")

    urls = project.get("urls") or {}
    for key in ("Homepage", "Repository", "Changelog"):
        if not urls.get(key):
            issues.append(f"project.urls.{key} is required")

    required_files = [
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "SUPPORT.md",
        "docs/contributor-starter.md",
        "docs/good-first-issues.md",
        "docs/module-ownership.md",
        "docs/weekly-maintainer-loop.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    ]
    for filename in required_files:
        if not (root / filename).exists():
            issues.append(f"open source metadata file is missing: {filename}")

    template_snippets = {
        "README.md": [
            "10-minute success path",
            "data.quality",
            "--strict-quality",
            "E_EMPTY_RESULT",
            "scripts/release_readiness.py",
            "scripts/check_release_publication.py",
            "Real Demo Case Proposal",
            "docs/good-first-issues.md",
            "weekly-maintainer-loop.md",
            "next_actions",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
            "github.com-1.0.0.cliany-adapter.tar.gz",
        ],
        "README.zh.md": [
            "10 分钟成功路径",
            "data.quality",
            "--strict-quality",
            "E_EMPTY_RESULT",
            "scripts/release_readiness.py",
            "scripts/check_release_publication.py",
            "Real Demo Case Proposal",
            "docs/good-first-issues.md",
            "weekly-maintainer-loop.md",
            "next_actions",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
            "github.com-1.0.0.cliany-adapter.tar.gz",
        ],
        "docs/contributor-starter.md": [
            "good-first-issues.md",
            "module-ownership.md",
            "CLIANY_QA_OFFLINE=1",
            "Real Demo Case Proposal",
            "Candidate Promotion Tasks",
            "Issue Body Template",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
            "AXTree snapshot",
        ],
        "docs/module-ownership.md": [
            "Owner area",
            "Adapter lifecycle",
            "Case catalog",
            "Release operations",
            "scripts/check_release_publication.py",
            "Contributor experience",
            "CLIANY_QA_OFFLINE=1",
            "python scripts/validate_cases.py --strict",
            "tests/test_release_publication.py",
            "~/.cliany-site/",
        ],
        "docs/good-first-issues.md": [
            "Good First Issues",
            "CLIANY_QA_OFFLINE=1",
            "python scripts/validate_cases.py --strict",
            "python scripts/release_readiness.py",
            "promotion",
            "Candidate Promotion Tasks",
            "Issue Body Template",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
            "Issue 拆分清单",
            "推荐验证命令",
            "~/.cliany-site/",
        ],
        "docs/roadmap-2026-q3.md": [
            "weekly-maintainer-loop.md",
            "每周维护者循环",
        ],
        "docs/release-cadence.md": [
            "weekly-maintainer-loop.md",
            "每周维护者循环",
            "scripts/check_release_publication.py",
            "python scripts/check_release_publication.py --remote --json",
            "python scripts/check_release_publication.py --remote --report",
        ],
        "docs/weekly-maintainer-loop.md": [
            "python scripts/release_readiness.py --json",
            "python scripts/validate_cases.py --strict",
            "CLIANY_QA_OFFLINE=1",
            "commit days N/3",
        ],
        "docs/quickstart-10min.md": [
            "10 分钟成功路径",
            "cliany-site doctor",
            "capabilities",
            "recommended_next_step",
            "demo_adapter_quickstart",
            "cliany-site market install ./issues.apache.org.cliany-adapter-v0.14.0.tar.gz",
            "cliany-site verify issues.apache.org --json",
            "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json",
            "没有 LLM key",
            "Real Demo Case Proposal",
            "python scripts/validate_cases.py --strict",
        ],
        "site/index.html": [
            "10-Minute Success Path",
            "issues.apache.org.cliany-adapter-v0.14.0.tar.gz",
            "cliany-site verify issues.apache.org --json",
            "Real Demo Case Proposal",
            "docs/weekly-maintainer-loop.md",
            "next_actions",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
        ],
        "site/docs/index.html": [
            "10 分钟成功路径",
            "不需要先配置 LLM key",
            "issues.apache.org.cliany-adapter-v0.14.0.tar.gz",
            "cliany-site verify issues.apache.org --json",
            "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
        ],
        ".github/PULL_REQUEST_TEMPLATE.md": [
            "python scripts/validate_cases.py --strict",
            "python scripts/release_readiness.py --json",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
            "CLIANY_QA_OFFLINE=1",
            "~/.cliany-site/",
        ],
        ".github/ISSUE_TEMPLATE/bug_report.yml": [
            "id: target_url",
            "id: error_code",
            "id: axtree_snapshot",
            "id: doctor_output",
        ],
        ".github/ISSUE_TEMPLATE/feature_request.yml": [
            "id: problem",
            "id: solution",
            "id: checklist",
        ],
        ".github/ISSUE_TEMPLATE/case_proposal.yml": [
            'labels: ["case-proposal"]',
            "id: target_url",
            "id: expected_command",
            "id: example_output",
            "id: promotion",
            "Candidate Promotion Tasks",
            "Issue Body Template",
            "primary_next_task_runbook",
            "case_promotion_evidence_primary_runbook_steps",
            "adapter_package",
            "metadata_validation",
            "online_smoke",
            "python scripts/validate_cases.py --strict",
            "degraded",
        ],
        ".github/ISSUE_TEMPLATE/config.yml": [
            "blank_issues_enabled: false",
            "security/advisories/new",
            "Documentation",
        ],
    }
    for filename, snippets in template_snippets.items():
        full_path = root / filename
        if not full_path.exists():
            continue
        text = full_path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                issues.append(f"open source metadata file missing snippet: {filename}: {snippet}")

    return ProjectMetadataReport(ok=not issues, path=str(path), issues=issues)


def _build_package_gate_report(
    *,
    packages_dir: Path | None,
    require_packages: bool,
    cases: CasesReport,
) -> PackageGateReport:
    issues: list[str] = []
    if require_packages and not cases.checked_packages:
        issues.append("case package validation is required; pass --packages-dir")

    failed_count = 0
    missing_count = 0
    invalid_count = 0
    repair_actions: list[str] = []
    for case in cases.cases:
        package = case.package
        if package is None or package.get("ok"):
            continue
        failed_count += 1
        if package.get("status") == "missing":
            missing_count += 1
        if package.get("status") == "invalid":
            invalid_count += 1
        for action in package.get("next_actions") or []:
            action_text = str(action)
            if action_text not in repair_actions:
                repair_actions.append(action_text)

    if require_packages and cases.checked_packages and failed_count:
        issues.append(f"case package validation failed: {failed_count} failing package(s)")

    return PackageGateReport(
        ok=not issues,
        required=require_packages,
        checked=cases.checked_packages,
        packages_dir=str(packages_dir) if packages_dir is not None else None,
        issues=issues,
        failed_count=failed_count,
        missing_count=missing_count,
        invalid_count=invalid_count,
        repair_action_count=len(repair_actions),
        primary_repair_action=repair_actions[0] if repair_actions else None,
    )


def _cadence_blockers(report: CadenceReport) -> list[str]:
    blockers: list[str] = []
    if not report.daily_release_limit_ok:
        blockers.append(
            "daily release tags "
            f"{report.release_count_today}/{report.max_daily_releases} exceed the allowed maximum"
        )
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


def _target_daily_release_limit_context(
    report: CadenceReport,
    target_version: str | None,
    *,
    release_tag: str | None,
) -> tuple[str, int] | None:
    if release_tag:
        return None
    target_tag = _target_tag_name(target_version)
    if (
        target_tag is None
        or target_tag == report.latest_tag
        or target_tag in report.release_tags_today
        or report.release_count_today < report.max_daily_releases
    ):
        return None
    return target_tag, report.release_count_today + 1


def _target_daily_release_limit_blocker(
    report: CadenceReport,
    target_version: str | None,
    *,
    release_tag: str | None,
) -> str | None:
    context = _target_daily_release_limit_context(
        report,
        target_version,
        release_tag=release_tag,
    )
    if context is None:
        return None
    target_tag, projected_count = context
    return (
        f"creating target tag {target_tag} today would exceed the daily release cap "
        f"{projected_count}/{report.max_daily_releases}"
    )


def _has_target_daily_release_limit_blocker(blockers: list[str]) -> bool:
    return any(
        blocker.startswith("creating target tag ")
        and "today would exceed the daily release cap" in blocker
        for blocker in blockers
    )


def _target_daily_release_limit_next_action(report: ReadinessReport) -> str | None:
    target_daily_context = _target_daily_release_limit_context(
        report.cadence,
        report.target_version,
        release_tag=report.release_tag,
    )
    if target_daily_context is None:
        return None
    target_tag, projected_count = target_daily_context
    return (
        "Pause release tagging until the next day; creating "
        f"`{target_tag}` today would make release tags "
        f"`{projected_count}/{report.cadence.max_daily_releases}`."
    )


def _mentions_create_new_release_tag(action: str) -> bool:
    return "create a new release tag at HEAD" in action


def _publication_blockers(report: PublicationReport) -> list[str]:
    blockers: list[str] = []
    if report.ok:
        return blockers
    if not report.worktree_clean:
        blockers.append("publication worktree is dirty")
    if report.branch_published is not True:
        blockers.append("latest local release is not published")
    if report.latest_tag and not report.tag_points_at_head:
        blockers.append("latest release tag does not point at HEAD")
    if report.tag_published is not True:
        blockers.append("latest local release tag is not published")
    if not report.latest_tag:
        blockers.append("release tag is missing")
    return blockers


def build_report(
    root: Path = ROOT,
    *,
    today: date | None = None,
    min_commit_days: int = 3,
    max_daily_releases: int = 3,
    remote_check: bool = False,
    remote_name: str = "origin",
    min_case_assets: int = MIN_CASE_ASSETS,
    target_version: str | None = None,
    release_tag: str | None = None,
    packages_dir: Path | None = None,
    require_packages: bool = False,
) -> ReadinessReport:
    current_version = _project_version(root)
    expected_target = target_version or (
        _strip_v_prefix(release_tag) if release_tag else _next_patch_version(current_version)
    )
    draft_base_version = _previous_tag_version(root, release_tag) if release_tag else current_version
    cadence = build_cadence_report(
        root,
        today=today or date.today(),
        min_commit_days=min_commit_days,
        max_daily_releases=max_daily_releases,
    )
    cases = build_cases_report(root, packages_dir=packages_dir)
    draft = _build_draft_report(root, draft_base_version or current_version, expected_target)
    ci = _build_ci_report(root)
    release_workflow = _build_release_workflow_report(root)
    project_metadata = _build_project_metadata_report(root)
    publication = build_publication_report(root, remote_check=remote_check, remote=remote_name)
    package_gate = _build_package_gate_report(
        packages_dir=packages_dir,
        require_packages=require_packages,
        cases=cases,
    )

    blockers = _cadence_blockers(cadence)
    target_daily_blocker = _target_daily_release_limit_blocker(
        cadence,
        expected_target,
        release_tag=release_tag,
    )
    if target_daily_blocker:
        blockers.append(target_daily_blocker)
    if release_tag and current_version != expected_target:
        blockers.append(f"release tag {release_tag} != pyproject version {current_version}")
    if release_tag and draft_base_version is None:
        blockers.append(f"previous tag for release {release_tag} could not be determined")
    if release_tag and not _tag_points_at_head(root, release_tag):
        blockers.append(f"release tag {release_tag} does not point at HEAD")
    if not cases.ok:
        blockers.append("case catalog validation failed")
    if cases.total < min_case_assets:
        blockers.append(f"case assets {cases.total}/{min_case_assets}")
    if not draft.ok:
        blockers.append("release draft validation failed")
    if not ci.ok:
        blockers.append("CI release gates validation failed")
    if not release_workflow.ok:
        blockers.append("release workflow validation failed")
    if not project_metadata.ok:
        blockers.append("project metadata validation failed")
    if not package_gate.ok:
        if package_gate.checked:
            blockers.append("case package validation failed")
        else:
            blockers.append("case package validation not run")

    return ReadinessReport(
        ok=not blockers,
        current_version=current_version,
        target_version=expected_target,
        release_mode="tagged" if release_tag else "target",
        release_tag=release_tag,
        blockers=blockers,
        min_case_assets=min_case_assets,
        cadence=cadence,
        cases=cases,
        draft=draft,
        ci=ci,
        release_workflow=release_workflow,
        project_metadata=project_metadata,
        package_gate=package_gate,
        publication=publication,
        remote_check=remote_check,
        remote_name=remote_name,
    )


def _print_text(report: ReadinessReport) -> None:
    publication_payload = _publication_payload(report)
    publication_summary = _publication_summary(publication_payload)
    publication_ref_context = _publication_ref_context(publication_payload)
    publication_blockers = _publication_blockers(report.publication)
    tag_publish_decision = publication_payload["tag_publish_decision"]
    publication_next_actions = list(publication_payload["next_actions"])
    publication_publish_commands = list(publication_payload["publish_commands"])
    next_actions = _next_action_lines(report)
    standard_release_flow = _standard_release_flow(
        report,
        publication_payload=publication_payload,
        next_actions=next_actions,
    )
    print("=== cliany-site release readiness ===")
    print(f"current_version: {report.current_version}")
    print(f"target_version: {report.target_version}")
    print(f"ok: {report.ok}")
    if report.blockers:
        print("blockers:")
        for blocker in report.blockers:
            print(f"- {blocker}")
    print(f"cadence: {report.cadence.ok}")
    print(
        f"cases: {report.cases.ok} "
        f"(active {report.cases.active}, candidate {report.cases.candidate}, "
        f"known_gap {report.cases.known_gap}, total {report.cases.total}, "
        f"min_assets {report.min_case_assets})"
    )
    command_plan_summary = report.cases.promotion_command_plan_summary
    print(
        "candidate_command_plan_summary: "
        f"all_declared={str(bool(command_plan_summary.get('all_declared'))).lower()}, "
        f"commands={command_plan_summary.get('command_count')}/"
        f"{command_plan_summary.get('expected_command_count')}, "
        f"missing={command_plan_summary.get('missing_command_count')}"
    )
    print(f"draft: {report.draft.ok}")
    print(f"ci: {report.ci.ok}")
    print(f"release_workflow: {report.release_workflow.ok}")
    print(f"project_metadata: {report.project_metadata.ok}")
    print(f"publication: {publication_payload['ok']}")
    print(
        "publication_summary: "
        f"status={publication_summary['status']}, "
        f"worktree_clean={str(bool(publication_summary['worktree_clean'])).lower()}, "
        f"ahead={publication_summary['ahead_count']}, "
        f"tag_decision={publication_summary['tag_decision_status']}, "
        f"target_tag={publication_summary['target_tag']}, "
        f"publish_commands={publication_summary['publish_command_count']}"
    )
    print(f"publication_summary_sha256: {_stable_json_sha256(publication_summary)}")
    print(f"publication_summary_primary_next_action: {publication_summary['primary_next_action']}")
    print(f"publication_summary_primary_publish_command: {publication_summary['primary_publish_command']}")
    print(f"publication_blocker_count: {len(publication_blockers)}")
    print(f"publication_blockers_sha256: {_stable_json_sha256(publication_blockers)}")
    if publication_blockers:
        print(f"publication_primary_blocker: {publication_blockers[0]}")
        print("publication_blockers:")
        for blocker in publication_blockers:
            print(f"- {blocker}")
    print(
        "publication_worktree: "
        f"clean={str(bool(publication_payload['worktree_clean'])).lower()}, "
        f"status_count={len(publication_payload['worktree_status'])}"
    )
    if publication_payload["worktree_status"]:
        print("publication_worktree_status:")
        for status_line in publication_payload["worktree_status"]:
            print(f"- {status_line}")
    print(
        "publication_ref_context: "
        f"branch={publication_ref_context['branch'] or '(detached)'}, "
        f"upstream={publication_ref_context['upstream'] or '(none)'}, "
        f"ahead={publication_ref_context['ahead_count']}, "
        f"latest_tag={publication_ref_context['latest_tag'] or '(none)'}, "
        f"tag_points_at_head={str(bool(publication_ref_context['tag_points_at_head'])).lower()}"
    )
    print(
        "publication_tag_publish_decision: "
        f"status={tag_publish_decision['status']}, "
        f"can_push_tag={str(bool(tag_publish_decision['can_push_tag'])).lower()}"
    )
    if tag_publish_decision.get("required_action"):
        print(f"publication_tag_required_action: {tag_publish_decision['required_action']}")
    if tag_publish_decision.get("target_tag"):
        print(f"publication_target_tag: {tag_publish_decision['target_tag']}")
        print(f"publication_target_tag_status: {tag_publish_decision['target_tag_status']}")
        print(
            "publication_target_tag_release_gate_status: "
            f"{tag_publish_decision['target_tag_release_gate_status']}"
        )
        print(
            "publication_target_tag_release_gate_blocker_count: "
            f"{tag_publish_decision['target_tag_release_gate_blocker_count']}"
        )
        if tag_publish_decision.get("target_tag_release_gate_primary_blocker"):
            print(
                "publication_target_tag_release_gate_primary_blocker: "
                f"{tag_publish_decision['target_tag_release_gate_primary_blocker']}"
            )
        print(f"publication_target_tag_commands_sha256: {tag_publish_decision['target_tag_commands_sha256']}")
        if tag_publish_decision.get("target_tag_primary_command"):
            print(
                "publication_target_tag_primary_command: "
                f"{tag_publish_decision['target_tag_primary_command']}"
            )
    print(f"publication_next_action_count: {len(publication_next_actions)}")
    print(f"publication_next_actions_sha256: {_stable_json_sha256(publication_next_actions)}")
    if publication_next_actions:
        print(f"publication_primary_next_action: {publication_next_actions[0]}")
    if publication_next_actions:
        print("publication_next_actions:")
        for action in publication_next_actions:
            print(f"- {action}")
    print(f"publication_publish_command_count: {len(publication_publish_commands)}")
    print(
        "publication_publish_commands_sha256: "
        f"{_stable_json_sha256(publication_publish_commands)}"
    )
    if publication_publish_commands:
        print(f"publication_primary_publish_command: {publication_publish_commands[0]}")
    if publication_publish_commands:
        print("publication_publish_commands:")
        for command in publication_publish_commands:
            print(f"- {command}")
    print(
        "standard_release_flow: "
        f"status={standard_release_flow['status']}, "
        f"target_tag={standard_release_flow['target_tag']}, "
        f"commands={standard_release_flow['command_count']}"
    )
    print(f"standard_release_flow_sha256: {_stable_json_sha256(standard_release_flow)}")
    print(
        "standard_release_flow_primary_next_action: "
        f"{standard_release_flow['primary_next_action']}"
    )
    print(
        "standard_release_flow_commands_sha256: "
        f"{standard_release_flow['commands_sha256']}"
    )
    print(f"package_gate: {report.package_gate.ok}")
    print(
        "package_gate_summary: "
        f"checked={str(report.package_gate.checked).lower()}, "
        f"failed={report.package_gate.failed_count}, "
        f"missing={report.package_gate.missing_count}, "
        f"invalid={report.package_gate.invalid_count}, "
        f"repair_actions={report.package_gate.repair_action_count}"
    )
    if report.package_gate.primary_repair_action:
        print(f"package_gate_primary_repair_action: {report.package_gate.primary_repair_action}")
    if next_actions:
        print("next_actions:")
        for action in next_actions:
            print(f"- {action}")


def _report_issue_lines(report: ReadinessReport) -> list[str]:
    lines: list[str] = []
    for blocker in report.blockers:
        if blocker.startswith("release tag "):
            lines.append(f"- `release_tag`: {blocker}")
    for issue in _cadence_blockers(report.cadence):
        lines.append(f"- `cadence`: {issue}")
    for case in report.cases.cases:
        for issue in case.issues:
            lines.append(f"- `cases/{case.id}`: {issue}")
        if case.package is not None:
            package_issues = case.package.get("issues") or []
            if case.package.get("issue"):
                package_issues = [*package_issues, str(case.package["issue"])]
            for issue in package_issues:
                lines.append(f"- `cases/{case.id}/package`: {issue}")
    if report.cases.total < report.min_case_assets:
        lines.append(f"- `cases`: case assets {report.cases.total}/{report.min_case_assets}")
    for gate_name, gate in (
        ("draft", report.draft),
        ("ci", report.ci),
        ("release_workflow", report.release_workflow),
        ("project_metadata", report.project_metadata),
        ("package_gate", report.package_gate),
    ):
        for issue in gate.issues:
            lines.append(f"- `{gate_name}`: {issue}")
    return lines


def _case_package_next_action_lines(report: ReadinessReport) -> list[str]:
    action_cases: dict[str, list[str]] = {}
    for case in report.cases.cases:
        package = case.package
        if package is None or package.get("ok"):
            continue
        for action in package.get("next_actions") or []:
            action_text = str(action)
            action_cases.setdefault(action_text, [])
            if case.id not in action_cases[action_text]:
                action_cases[action_text].append(case.id)

    lines: list[str] = []
    for action, case_ids in action_cases.items():
        if len(case_ids) > 1:
            lines.append(f"Package checks: {action}")
        else:
            lines.append(f"`{case_ids[0]}` package: {action}")
    return lines


def _publication_publish_commands(report: ReadinessReport) -> list[str]:
    return [str(command) for command in report.publication.to_dict()["publish_commands"]]


def _publication_next_actions(report: ReadinessReport) -> list[str]:
    return [str(action) for action in _publication_payload(report)["next_actions"]]


def _publication_payload(report: ReadinessReport) -> dict[str, Any]:
    payload = report.publication.to_dict()
    return {
        **payload,
        "tag_publish_decision": _publication_tag_publish_decision(
            payload,
            report.target_version,
            readiness_blockers=report.blockers,
        ),
    }


def _publication_tag_publish_decision(
    publication_payload: dict[str, Any],
    target_version: str | None,
    *,
    readiness_blockers: list[str] | None = None,
) -> dict[str, Any]:
    decision = dict(publication_payload["tag_publish_decision"])
    target_tag = _target_tag_name(target_version)
    if target_tag is None:
        return decision

    blockers = list(readiness_blockers or [])
    latest_tag = decision.get("latest_tag")
    tag_points_at_head = bool(decision.get("tag_points_at_head", False))
    target_tag_matches_latest = latest_tag == target_tag
    remote = str(publication_payload.get("remote") or "origin")
    create_command = f"git tag {shlex.quote(target_tag)}"
    push_command = f"git push {shlex.quote(remote)} {shlex.quote(target_tag)}"

    if _has_target_daily_release_limit_blocker(blockers):
        target_status = "blocked_by_daily_release_cap"
        required_action = f"Pause release tagging until the next day before creating target tag `{target_tag}`."
        commands = []
    elif target_tag_matches_latest and tag_points_at_head:
        target_status = "current_tag_at_head"
        required_action = decision.get("required_action")
        commands: list[str] = []
    elif not bool(publication_payload.get("worktree_clean", True)):
        target_status = "blocked_by_worktree"
        required_action = (
            "Commit, stash, or discard local worktree changes before creating "
            f"target tag `{target_tag}`."
        )
        commands = [create_command, push_command]
    else:
        target_status = "create_target_tag_at_head"
        required_action = (
            f"After final release readiness is clean, create target tag `{target_tag}` at HEAD "
            "and push it after the branch is published."
        )
        commands = [create_command, push_command]

    return {
        **decision,
        "target_tag": target_tag,
        "target_tag_matches_latest": target_tag_matches_latest,
        "target_tag_status": target_status,
        "target_tag_required_action": required_action,
        "target_tag_command_count": len(commands),
        "target_tag_commands_sha256": _stable_json_sha256(commands),
        "target_tag_primary_command": commands[0] if commands else None,
        "target_tag_commands": commands,
        "target_tag_release_gate_status": (
            "blocked_by_readiness" if blockers else "ready_for_publication_review"
        ),
        "target_tag_release_gate_blocker_count": len(blockers),
        "target_tag_release_gate_blockers_sha256": _stable_json_sha256(blockers),
        "target_tag_release_gate_primary_blocker": blockers[0] if blockers else None,
        "target_tag_release_gate_required_action": (
            f"Clear release readiness blockers before creating target tag `{target_tag}`."
            if blockers
            else required_action
        ),
        "target_tag_release_gate_blockers": blockers,
    }


def _target_tag_name(target_version: str | None) -> str | None:
    if not target_version:
        return None
    version = str(target_version).strip()
    if not version:
        return None
    return version if version.startswith("v") else f"v{version}"


def _remote_audit_args(*, remote_check: bool, remote_name: str) -> str:
    args: list[str] = []
    if remote_check:
        args.append("--remote")
    if remote_name != "origin":
        args.extend(["--remote-name", shlex.quote(remote_name)])
    return f" {' '.join(args)}" if args else ""


def _release_readiness_strict_command(report: ReadinessReport) -> str:
    remote_args = _remote_audit_args(
        remote_check=bool(getattr(report, "remote_check", False)),
        remote_name=str(getattr(report, "remote_name", "origin") or "origin"),
    )
    return (
        "python scripts/release_readiness.py --strict "
        f"--target-version {shlex.quote(report.target_version)}{remote_args}"
    )


def _remote_publication_audit_command(report: ReadinessReport) -> str:
    remote_args = _remote_audit_args(
        remote_check=True,
        remote_name=str(getattr(report, "remote_name", "origin") or "origin"),
    )
    return f"python scripts/check_release_publication.py{remote_args} --json"


def _publication_ref_context(publication_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_root": publication_payload["repo_root"],
        "branch": publication_payload["branch"],
        "upstream": publication_payload["upstream"],
        "remote": publication_payload["remote"],
        "local_head": publication_payload["local_head"],
        "upstream_head": publication_payload["upstream_head"],
        "ahead_count": publication_payload["ahead_count"],
        "behind_count": publication_payload["behind_count"],
        "latest_tag": publication_payload["latest_tag"],
        "tag_commit": publication_payload["tag_commit"],
        "tag_points_at_head": publication_payload["tag_points_at_head"],
        "tag_commit_in_upstream": publication_payload["tag_commit_in_upstream"],
        "branch_published": publication_payload["branch_published"],
        "tag_published": publication_payload["tag_published"],
        "remote_checked": publication_payload["remote_checked"],
    }


def _publication_summary(publication_payload: dict[str, Any]) -> dict[str, Any]:
    next_actions = list(publication_payload["next_actions"])
    publish_commands = list(publication_payload["publish_commands"])
    tag_publish_decision = publication_payload["tag_publish_decision"]
    return {
        "ok": publication_payload["ok"],
        "status": "published" if publication_payload["ok"] else "blocked",
        "worktree_clean": publication_payload["worktree_clean"],
        "branch": publication_payload["branch"],
        "upstream": publication_payload["upstream"],
        "remote": publication_payload["remote"],
        "ahead_count": publication_payload["ahead_count"],
        "behind_count": publication_payload["behind_count"],
        "latest_tag": publication_payload["latest_tag"],
        "tag_points_at_head": publication_payload["tag_points_at_head"],
        "tag_decision_status": tag_publish_decision["status"],
        "tag_can_push": tag_publish_decision["can_push_tag"],
        "target_tag": tag_publish_decision.get("target_tag"),
        "target_tag_status": tag_publish_decision.get("target_tag_status"),
        "target_tag_primary_command": tag_publish_decision.get("target_tag_primary_command"),
        "target_tag_release_gate_status": tag_publish_decision.get(
            "target_tag_release_gate_status"
        ),
        "target_tag_release_gate_blocker_count": tag_publish_decision.get(
            "target_tag_release_gate_blocker_count"
        ),
        "target_tag_release_gate_primary_blocker": tag_publish_decision.get(
            "target_tag_release_gate_primary_blocker"
        ),
        "next_action_count": len(next_actions),
        "primary_next_action": next_actions[0] if next_actions else None,
        "publish_command_count": len(publish_commands),
        "primary_publish_command": publish_commands[0] if publish_commands else None,
    }


def _standard_release_flow(
    report: ReadinessReport,
    *,
    publication_payload: dict[str, Any],
    next_actions: list[str],
) -> dict[str, Any]:
    tag_publish_decision = publication_payload["tag_publish_decision"]
    target_tag = tag_publish_decision.get("target_tag") or _target_tag_name(report.target_version)
    strict_command = _release_readiness_strict_command(report)
    validation_command = "CLIANY_QA_OFFLINE=1 pytest tests/ -q"
    case_validation_command = "python scripts/validate_cases.py --strict"
    release_notes_action = (
        f"Move CHANGELOG.md Unreleased entries into `## [{report.target_version}] - "
        "<date>`."
    )
    version_action = f"Update pyproject.toml project.version to `{report.target_version}`."
    target_tag_commands = [
        str(command) for command in tag_publish_decision.get("target_tag_commands") or []
    ]
    remote_audit_command = _remote_publication_audit_command(report)

    commands = [
        strict_command,
        validation_command,
        case_validation_command,
        *[str(command) for command in publication_payload["publish_commands"]],
        *target_tag_commands,
        remote_audit_command,
    ]
    commands = list(dict.fromkeys(command for command in commands if command))
    blockers = [*report.blockers, *_publication_blockers(report.publication)]
    status = "blocked" if blockers else "ready"
    primary_next_action = (
        next_actions[0]
        if next_actions
        else f"Run `{strict_command}` before tagging `{target_tag}`."
    )

    return {
        "status": status,
        "target_version": report.target_version,
        "target_tag": target_tag,
        "blocker_count": len(blockers),
        "blockers_sha256": _stable_json_sha256(blockers),
        "blockers": blockers,
        "primary_next_action": primary_next_action,
        "command_count": len(commands),
        "commands_sha256": _stable_json_sha256(commands),
        "commands": commands,
        "steps": [
            {
                "name": "strict_release_readiness",
                "status": "blocked" if report.blockers else "ready",
                "command": strict_command,
            },
            {
                "name": "release_notes",
                "status": "pending",
                "action": release_notes_action,
            },
            {
                "name": "version_bump",
                "status": "pending" if report.current_version != report.target_version else "ready",
                "action": version_action,
            },
            {
                "name": "offline_validation",
                "status": "pending",
                "commands": [validation_command, case_validation_command],
            },
            {
                "name": "publish_branch",
                "status": "blocked" if not publication_payload["worktree_clean"] else "pending",
                "commands": list(publication_payload["publish_commands"]),
            },
            {
                "name": "target_tag",
                "status": tag_publish_decision.get("target_tag_status"),
                "commands": target_tag_commands,
            },
            {
                "name": "remote_publication_audit",
                "status": "pending",
                "command": remote_audit_command,
            },
        ],
    }


def _stable_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _next_action_lines(report: ReadinessReport) -> list[str]:
    lines: list[str] = []
    target_daily_action = _target_daily_release_limit_next_action(report)
    if target_daily_action:
        lines.append(target_daily_action)
    if not report.publication.ok:
        publication_payload = _publication_payload(report)
        publication_primary_next_action = _publication_summary(publication_payload)[
            "primary_next_action"
        ]
        if publication_primary_next_action and not (
            target_daily_action and _mentions_create_new_release_tag(str(publication_primary_next_action))
        ):
            lines.append(str(publication_primary_next_action))
        target_tag_action = _target_tag_next_action(
            publication_payload["tag_publish_decision"]
        )
        if target_tag_action:
            lines.append(target_tag_action)
    if report.cadence.commit_day_count < report.cadence.min_commit_days:
        missing_days = max(report.cadence.min_commit_days - report.cadence.commit_day_count, 0)
        lines.append(
            "Ship verified slices on "
            f"`{missing_days}` more unique commit days this week; current commit days are "
            f"`{report.cadence.commit_day_count}/{report.cadence.min_commit_days}`. "
            "Use `docs/weekly-maintainer-loop.md` to pick the next slice."
        )
    if not report.cadence.daily_release_limit_ok:
        lines.append(
            "Pause release tagging until the next day; today's release tags are "
            f"`{report.cadence.release_count_today}/{report.cadence.max_daily_releases}`: "
            f"`{', '.join(report.cadence.release_tags_today)}`."
        )
    if report.cadence.dirty:
        lines.append("Commit or revert the working tree before tagging a release.")
    if any(blocker.startswith("release tag ") and "does not point at HEAD" in blocker for blocker in report.blockers):
        lines.append("Check out the release tag commit before running `--release-tag` preflight.")
    if not report.cadence.tag_matches_version:
        lines.append("Align `pyproject.toml` version and the latest release tag before publishing.")
    if not report.cadence.changelog_ok:
        lines.append("Update `CHANGELOG.md` Unreleased content and compare link before release.")
    if not report.cases.ok:
        lines.append("Run `python scripts/validate_cases.py --strict` and fix the listed case catalog issues.")
        lines.extend(_case_package_next_action_lines(report))
    if report.cases.total < report.min_case_assets:
        lines.append(
            "Add verified active or candidate case assets until the catalog reaches "
            f"`{report.min_case_assets}` tracked cases."
        )
    if not report.draft.ok:
        lines.append(
            "Update the target release draft under `docs/releases/` with value, risks, validation, and blockers."
        )
    if not report.ci.ok:
        lines.append("Restore the default zero-key CI release gates before merging.")
    if not report.release_workflow.ok:
        lines.append("Restore tag release preflight, build, GitHub Release, and PyPI publishing checks.")
    if not report.project_metadata.ok:
        lines.append("Restore PyPI metadata and open-source community entrypoints required by project metadata gate.")
    if not report.package_gate.ok:
        if report.package_gate.checked and report.package_gate.failed_count:
            lines.append(
                "Fix or rebuild the failing case packages listed in `Case Package Checks`, then rerun "
                "`python scripts/release_readiness.py --packages-dir ~/.cliany-site/packages --require-packages`."
            )
        else:
            lines.append(
                "Re-run release readiness with `--packages-dir ~/.cliany-site/packages --require-packages` "
                "after demo adapter packages are available."
            )
    deduped: list[str] = []
    for line in lines:
        if line not in deduped:
            deduped.append(line)
    return deduped


def _target_tag_next_action(tag_publish_decision: dict[str, Any]) -> str | None:
    if tag_publish_decision.get("target_tag_status") not in {
        "blocked_by_worktree",
        "create_target_tag_at_head",
    }:
        return None
    action = tag_publish_decision.get("target_tag_required_action")
    if not action:
        return None

    commands = tag_publish_decision.get("target_tag_commands")
    if not isinstance(commands, list) or not commands:
        return str(action)
    command_text = " then ".join(f"`{command}`" for command in commands)
    return f"{action} Commands: {command_text}."


def _markdown_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _candidate_promotion_rows(report: ReadinessReport) -> list[str]:
    rows: list[str] = []
    for case in report.cases.cases:
        if case.status != "candidate" or case.promotion is None:
            continue
        cells = [_markdown_cell(case.id)]
        cells.extend(_markdown_cell(case.promotion.get(field_name)) for field_name in PROMOTION_FIELDS)
        rows.append(f"| `{cells[0]}` | {cells[1]} | {cells[2]} | {cells[3]} |")
    return rows


def _candidate_primary_next_task_rows(report: ReadinessReport) -> list[str]:
    primary_task = report.cases.promotion_evidence_summary.get("primary_next_task")
    if not isinstance(primary_task, dict) or not primary_task:
        return []

    return [
        (
            f"| `{_markdown_cell(primary_task.get('case_id'))}` | "
            f"`{_markdown_cell(primary_task.get('task'))}` | "
            f"`{_markdown_cell(primary_task.get('status'))}` | "
            f"{_markdown_cell(primary_task.get('evidence') or 'Not attached yet.')} | "
            f"{_markdown_cell(primary_task.get('next_action'))} |"
        )
    ]


def _case_promotion_primary_runbook(cases_report: Any) -> list[dict[str, Any]]:
    summary = getattr(cases_report, "promotion_evidence_summary", {})
    if not isinstance(summary, dict):
        return []
    runbook = summary.get("primary_next_task_runbook")
    if not isinstance(runbook, list):
        return []
    return [dict(step) for step in runbook if isinstance(step, dict)]


def _runbook_steps(runbook: list[dict[str, Any]]) -> list[str]:
    return [str(step.get("step") or "") for step in runbook if step.get("step")]


def _candidate_primary_runbook_rows(report: ReadinessReport) -> list[str]:
    runbook = _case_promotion_primary_runbook(report.cases)
    if not runbook:
        return []

    rows: list[str] = []
    for step in runbook:
        if not isinstance(step, dict):
            continue
        command = str(step.get("command") or "")
        command_cell = f"`{_markdown_cell(command)}`" if command else "No command."
        required = str(bool(step.get("required"))).lower()
        rows.append(
            "| "
            f"`{_markdown_cell(step.get('step'))}` | "
            f"{command_cell} | "
            f"`{required}` | "
            f"{_markdown_cell(step.get('handoff') or '-')} |"
        )
    return rows


def _candidate_command_plan_summary_lines(report: ReadinessReport) -> list[str]:
    summary = report.cases.promotion_command_plan_summary
    lines = [
        "",
        "## Candidate Promotion Command Plan Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| candidate_count | `{_markdown_cell(summary.get('candidate_count', 0))}` |",
        f"| command_count | `{_markdown_cell(summary.get('command_count', 0))}` |",
        f"| expected_command_count | `{_markdown_cell(summary.get('expected_command_count', 0))}` |",
        f"| missing_command_count | `{_markdown_cell(summary.get('missing_command_count', 0))}` |",
        f"| ready_candidate_count | `{_markdown_cell(summary.get('ready_candidate_count', 0))}` |",
        f"| all_declared | `{str(bool(summary.get('all_declared'))).lower()}` |",
        "",
        "| Case | Missing Tasks |",
        "|------|---------------|",
    ]
    missing_cases = list(summary.get("missing_cases") or [])
    if not missing_cases:
        lines.append("| - | - |")
        return lines
    for case in missing_cases:
        missing_tasks = ", ".join(str(task) for task in case.get("missing_tasks") or [])
        lines.append(f"| `{_markdown_cell(case.get('case_id'))}` | `{_markdown_cell(missing_tasks)}` |")
    return lines


def _publication_publish_command_lines(report: ReadinessReport) -> list[str]:
    publication_payload = _publication_payload(report)
    publication_summary = _publication_summary(publication_payload)
    publication_blockers = _publication_blockers(report.publication)
    ref_context = _publication_ref_context(publication_payload)
    tag_publish_decision = publication_payload["tag_publish_decision"]
    publication_next_actions = _publication_next_actions(report)
    commands = _publication_publish_commands(report)
    primary_next_action = publication_next_actions[0] if publication_next_actions else None
    primary_publish_command = commands[0] if commands else None
    lines = [
        "",
        "## Publication Publish Commands",
        "",
        f"- publication_ok: `{str(report.publication.ok).lower()}`",
        f"- publication_summary_status: `{_markdown_cell(publication_summary['status'])}`",
        f"- publication_summary_branch: `{_markdown_cell(publication_summary['branch'])}`",
        f"- publication_summary_ahead_count: `{_markdown_cell(publication_summary['ahead_count'])}`",
        f"- publication_summary_latest_tag: `{_markdown_cell(publication_summary['latest_tag'])}`",
        f"- publication_summary_target_tag: `{_markdown_cell(publication_summary['target_tag'])}`",
        f"- publication_summary_target_tag_status: `{_markdown_cell(publication_summary['target_tag_status'])}`",
        (
            "- publication_summary_target_tag_release_gate_status: "
            f"`{_markdown_cell(publication_summary['target_tag_release_gate_status'])}`"
        ),
        (
            "- publication_summary_target_tag_release_gate_blocker_count: "
            f"`{_markdown_cell(publication_summary['target_tag_release_gate_blocker_count'])}`"
        ),
        (
            "- publication_summary_target_tag_release_gate_primary_blocker: "
            f"`{_markdown_cell(publication_summary['target_tag_release_gate_primary_blocker'])}`"
        ),
        f"- publication_summary_sha256: `{_stable_json_sha256(publication_summary)}`",
        f"- publication_summary_primary_next_action: `{_markdown_cell(publication_summary['primary_next_action'])}`",
        (
            "- publication_summary_primary_publish_command: "
            f"`{_markdown_cell(publication_summary['primary_publish_command'])}`"
        ),
        f"- publication_blocker_count: `{len(publication_blockers)}`",
        f"- publication_blockers_sha256: `{_stable_json_sha256(publication_blockers)}`",
        f"- publication_primary_blocker: `{_markdown_cell(publication_blockers[0] if publication_blockers else None)}`",
        f"- tag_publish_decision: `{_markdown_cell(tag_publish_decision['status'])}`",
        f"- tag_can_push: `{str(bool(tag_publish_decision['can_push_tag'])).lower()}`",
        f"- tag_required_action: `{_markdown_cell(tag_publish_decision.get('required_action'))}`",
        f"- target_tag: `{_markdown_cell(tag_publish_decision.get('target_tag'))}`",
        f"- target_tag_status: `{_markdown_cell(tag_publish_decision.get('target_tag_status'))}`",
        (
            "- target_tag_release_gate_status: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_release_gate_status'))}`"
        ),
        (
            "- target_tag_release_gate_blocker_count: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_release_gate_blocker_count'))}`"
        ),
        (
            "- target_tag_release_gate_primary_blocker: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_release_gate_primary_blocker'))}`"
        ),
        (
            "- target_tag_release_gate_required_action: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_release_gate_required_action'))}`"
        ),
        (
            "- target_tag_release_gate_blockers_sha256: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_release_gate_blockers_sha256'))}`"
        ),
        (
            "- target_tag_required_action: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_required_action'))}`"
        ),
        f"- target_tag_commands_sha256: `{_markdown_cell(tag_publish_decision.get('target_tag_commands_sha256'))}`",
        (
            "- target_tag_primary_command: "
            f"`{_markdown_cell(tag_publish_decision.get('target_tag_primary_command'))}`"
        ),
        f"- publication_next_action_count: `{len(publication_next_actions)}`",
        f"- publication_next_actions_sha256: `{_stable_json_sha256(publication_next_actions)}`",
        f"- publication_primary_next_action: `{_markdown_cell(primary_next_action)}`",
        f"- publish_command_count: `{len(commands)}`",
        f"- publication_publish_commands_sha256: `{_stable_json_sha256(commands)}`",
        f"- primary_publish_command: `{_markdown_cell(primary_publish_command)}`",
        "",
    ]
    if publication_next_actions:
        lines.extend(
            [
                "### Publication Next Actions",
                "",
                *(f"- {action}" for action in publication_next_actions),
                "",
            ]
        )
    if publication_blockers:
        lines.extend(
            [
                "### Publication Blockers",
                "",
                *(f"- {blocker}" for blocker in publication_blockers),
                "",
            ]
        )
    lines.extend(
        [
            "### Publication Ref Context",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| branch | `{_markdown_cell(ref_context['branch'])}` |",
            f"| upstream | `{_markdown_cell(ref_context['upstream'])}` |",
            f"| remote | `{_markdown_cell(ref_context['remote'])}` |",
            f"| local_head | `{_markdown_cell(ref_context['local_head'])}` |",
            f"| upstream_head | `{_markdown_cell(ref_context['upstream_head'])}` |",
            f"| ahead_count | `{_markdown_cell(ref_context['ahead_count'])}` |",
            f"| behind_count | `{_markdown_cell(ref_context['behind_count'])}` |",
            f"| latest_tag | `{_markdown_cell(ref_context['latest_tag'])}` |",
            f"| tag_commit | `{_markdown_cell(ref_context['tag_commit'])}` |",
            f"| tag_points_at_head | `{str(bool(ref_context['tag_points_at_head'])).lower()}` |",
            f"| tag_commit_in_upstream | `{_markdown_cell(ref_context['tag_commit_in_upstream'])}` |",
            f"| branch_published | `{_markdown_cell(ref_context['branch_published'])}` |",
            f"| tag_published | `{_markdown_cell(ref_context['tag_published'])}` |",
            f"| remote_checked | `{str(bool(ref_context['remote_checked'])).lower()}` |",
            "",
        ]
    )
    lines.extend(
        [
            "### Publication Worktree Status",
            "",
            f"- clean: `{str(bool(publication_payload['worktree_clean'])).lower()}`",
            f"- status_count: `{len(publication_payload['worktree_status'])}`",
            "",
        ]
    )
    if publication_payload["worktree_status"]:
        lines.extend(["```text", *publication_payload["worktree_status"], "```", ""])
    else:
        lines.extend(["- Worktree is clean.", ""])
    if commands:
        lines.extend(["```bash", *commands, "```"])
    else:
        lines.append("- No publish commands are needed.")
    return lines


def _standard_release_flow_lines(report: ReadinessReport) -> list[str]:
    publication_payload = _publication_payload(report)
    next_actions = _next_action_lines(report)
    flow = _standard_release_flow(
        report,
        publication_payload=publication_payload,
        next_actions=next_actions,
    )
    lines = [
        "",
        "## Standard Release Flow",
        "",
        f"- standard_release_flow_status: `{_markdown_cell(flow['status'])}`",
        f"- standard_release_flow_target_version: `{_markdown_cell(flow['target_version'])}`",
        f"- standard_release_flow_target_tag: `{_markdown_cell(flow['target_tag'])}`",
        f"- standard_release_flow_blocker_count: `{flow['blocker_count']}`",
        f"- standard_release_flow_blockers_sha256: `{flow['blockers_sha256']}`",
        (
            "- standard_release_flow_primary_next_action: "
            f"`{_markdown_cell(flow['primary_next_action'])}`"
        ),
        f"- standard_release_flow_command_count: `{flow['command_count']}`",
        f"- standard_release_flow_commands_sha256: `{flow['commands_sha256']}`",
        f"- standard_release_flow_sha256: `{_stable_json_sha256(flow)}`",
        "",
        "### Standard Release Commands",
        "",
        *(f"- `{_markdown_cell(command)}`" for command in flow["commands"]),
        "",
        "### Standard Release Steps",
        "",
        "| Step | Status | Command / Action |",
        "|------|--------|------------------|",
    ]
    for step in flow["steps"]:
        command_or_action = step.get("command") or step.get("action")
        if command_or_action is None:
            command_or_action = "<br>".join(str(command) for command in step.get("commands") or [])
        lines.append(
            "| "
            f"`{_markdown_cell(step.get('name'))}` | "
            f"`{_markdown_cell(step.get('status'))}` | "
            f"{_markdown_cell(command_or_action)} |"
        )
    return lines


def _case_package_rows(report: ReadinessReport) -> list[str]:
    rows: list[str] = []
    for case in report.cases.cases:
        if case.package is None:
            continue
        package = case.package
        issues = list(package.get("issues") or [])
        if package.get("issue"):
            issues.append(str(package["issue"]))
        next_actions = list(package.get("next_actions") or [])
        rows.append(
            "| "
            f"`{_markdown_cell(case.id)}` | "
            f"`{_markdown_cell(package.get('status'))}` | "
            f"`{_markdown_cell(package.get('path'))}` | "
            f"{_markdown_cell('<br>'.join(issues) if issues else '-')} | "
            f"{_markdown_cell('<br>'.join(next_actions) if next_actions else '-')} |"
        )
    return rows


def _weekly_review_next_slice(report: ReadinessReport) -> str:
    next_actions = _next_action_lines(report)
    if next_actions:
        return next_actions[0]
    if (
        report.release_mode == "tagged"
        and report.current_version == report.target_version
        and report.cadence.tag_matches_version
        and report.cadence.commits_since_latest_tag == 0
    ):
        return f"Ready to publish verified tag `v{report.target_version}`."
    return f"Ready to tag `v{report.target_version}` after final validation."


def _weekly_review_rows(report: ReadinessReport) -> list[str]:
    next_slice = _weekly_review_next_slice(report)
    return [
        (
            "| Does this release help real users succeed? | "
            f"cases active `{report.cases.active}`, candidate `{report.cases.candidate}`; "
            f"total `{report.cases.total}/{report.min_case_assets}`; "
            f"release draft `{Path(report.draft.path).name}` |"
        ),
        (
            "| Is there reproducible evidence? | "
            f"cases `{str(report.cases.ok).lower()}`, ci `{str(report.ci.ok).lower()}`, "
            f"package gate `{str(report.package_gate.ok).lower()}` |"
        ),
        (
            "| Are docs and release notes synchronized? | "
            f"draft `{str(report.draft.ok).lower()}`, project metadata `{str(report.project_metadata.ok).lower()}` |"
        ),
        f"| Does the PR path stay zero-key by default? | ci `{str(report.ci.ok).lower()}` |",
        (
            "| Does the week have enough commit days? | "
            f"`{report.cadence.commit_day_count}/{report.cadence.min_commit_days}`: "
            f"{', '.join(report.cadence.commit_days) or '-'} |"
        ),
        (
            "| Is today's release count within the cap? | "
            f"`{report.cadence.release_count_today}/{report.cadence.max_daily_releases}`: "
            f"{', '.join(report.cadence.release_tags_today) or '-'} |"
        ),
        f"| What is the next smallest release slice? | {_markdown_cell(next_slice)} |",
    ]


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
        f"| release_mode | `{report.release_mode}` |",
        f"| release_tag | `{report.release_tag or '-'}` |",
        f"| blockers | {blockers} |",
        "",
        "## Gates",
        "",
        "| Gate | Result | Detail |",
        "|------|--------|--------|",
        (
            f"| cadence | `{str(report.cadence.ok).lower()}` | "
            f"commit days `{report.cadence.commit_day_count}/{report.cadence.min_commit_days}`: {commit_days}; "
            f"daily releases `{report.cadence.release_count_today}/{report.cadence.max_daily_releases}` |"
        ),
        (
            f"| cases | `{str(report.cases.ok).lower()}` | "
            f"active `{report.cases.active}`, candidate `{report.cases.candidate}`, "
            f"known_gap `{report.cases.known_gap}`, total `{report.cases.total}`, "
            f"min_assets `{report.min_case_assets}` |"
        ),
        f"| draft | `{str(report.draft.ok).lower()}` | `{report.draft.path}` |",
        f"| ci | `{str(report.ci.ok).lower()}` | `{report.ci.path}` |",
        (
            f"| release_workflow | `{str(report.release_workflow.ok).lower()}` | "
            f"`{report.release_workflow.path}` |"
        ),
        f"| project_metadata | `{str(report.project_metadata.ok).lower()}` | `{report.project_metadata.path}` |",
        (
            f"| package_gate | `{str(report.package_gate.ok).lower()}` | "
            f"required `{str(report.package_gate.required).lower()}`, "
            f"checked `{str(report.package_gate.checked).lower()}`, "
            f"failed `{report.package_gate.failed_count}`, "
            f"missing `{report.package_gate.missing_count}`, "
            f"invalid `{report.package_gate.invalid_count}` |"
        ),
        "",
        "## Release Links",
        "",
        f"- CHANGELOG compare: {report.cadence.changelog_unreleased_compare_actual or '(missing)'}",
        f"- Release draft: `{report.draft.path}`",
        *_publication_publish_command_lines(report),
        *_standard_release_flow_lines(report),
        "",
        "## Weekly Review",
        "",
        "| Question | Evidence |",
        "|----------|----------|",
        *_weekly_review_rows(report),
    ]
    issue_lines = _report_issue_lines(report)
    if issue_lines:
        lines.extend(
            [
                "",
                "## Gate Issues",
                "",
                *issue_lines,
            ]
        )
    package_rows = _case_package_rows(report)
    if package_rows:
        lines.extend(
            [
                "",
                "## Case Package Checks",
                "",
                "| Case | Status | Package | Issues | Next Actions |",
                "|------|--------|---------|--------|--------------|",
                *package_rows,
            ]
        )
    primary_next_task_rows = _candidate_primary_next_task_rows(report)
    if primary_next_task_rows:
        lines.extend(
            [
                "",
                "## Candidate Primary Next Task",
                "",
                "| Case | Task | Status | Evidence | Next Action |",
                "|------|------|--------|----------|-------------|",
                *primary_next_task_rows,
            ]
        )
    primary_runbook_rows = _candidate_primary_runbook_rows(report)
    if primary_runbook_rows:
        lines.extend(
            [
                "",
                "## Candidate Primary Runbook",
                "",
                "| Step | Command | Required | Handoff |",
                "|------|---------|----------|---------|",
                *primary_runbook_rows,
            ]
        )
    if report.cases.candidate:
        lines.extend(_candidate_command_plan_summary_lines(report))
    candidate_rows = _candidate_promotion_rows(report)
    if candidate_rows:
        lines.extend(
            [
                "",
                "## Candidate Promotions",
                "",
                "| Case | Adapter Package | Metadata Validation | Online Smoke |",
                "|------|-----------------|---------------------|--------------|",
                *candidate_rows,
            ]
        )
    next_actions = _next_action_lines(report)
    if next_actions:
        lines.extend(
            [
                "",
                "## Next Actions",
                "",
                *(f"- {action}" for action in next_actions),
            ]
        )
    return "\n".join(lines) + "\n"


def _write_markdown_report(report: ReadinessReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown_report(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check readiness for the next cliany-site release.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when release readiness fails.")
    parser.add_argument("--min-days", type=int, default=3, help="Minimum unique commit days expected this week.")
    parser.add_argument("--max-daily-releases", type=int, default=3, help="Maximum release tags allowed per day.")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Check live remote branch and tag refs in the publication summary.",
    )
    parser.add_argument("--remote-name", default="origin", help="Fallback remote name when no upstream is configured.")
    parser.add_argument(
        "--min-case-assets",
        type=int,
        default=MIN_CASE_ASSETS,
        help="Minimum tracked active/candidate/known-gap case assets expected before release.",
    )
    parser.add_argument("--today", help="Override current date as YYYY-MM-DD, for tests or audits.")
    parser.add_argument("--target-version", help="Target release version. Defaults to next patch version.")
    parser.add_argument("--release-tag", help="Validate an already tagged release, e.g. v0.14.4.")
    parser.add_argument("--packages-dir", type=Path, help="Optional directory containing demo adapter packages.")
    parser.add_argument("--report", type=Path, help="Optional Markdown report path for release review.")
    parser.add_argument(
        "--require-packages",
        action="store_true",
        help="Require --packages-dir package validation before reporting release readiness.",
    )
    args = parser.parse_args(argv)
    if args.release_tag and args.target_version:
        parser.error("--release-tag and --target-version are mutually exclusive")

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None
    report = build_report(
        ROOT,
        today=today,
        min_commit_days=args.min_days,
        max_daily_releases=args.max_daily_releases,
        remote_check=args.remote,
        remote_name=args.remote_name,
        min_case_assets=args.min_case_assets,
        target_version=args.target_version,
        release_tag=args.release_tag,
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
