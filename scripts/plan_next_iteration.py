#!/usr/bin/env python3
"""Plan the next small cliany-site release slice from local project evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
PUBLICATION_PUBLISH_SCRIPT_PATH = "/tmp/cliany-publish-release.sh"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_release_publication import build_report as build_publication_report  # noqa: E402
from release_readiness import build_report as build_readiness_report  # noqa: E402


@dataclass(frozen=True)
class CandidatePromotion:
    case_id: str
    issue_title: str
    issue_labels: list[str]
    target_url: str
    commands: list[str]
    offline_commands: list[str]
    adapter_package: str
    metadata_validation: str
    online_smoke: str
    issue_body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "issue_title": self.issue_title,
            "issue_labels": self.issue_labels,
            "target_url": self.target_url,
            "commands": self.commands,
            "offline_commands": self.offline_commands,
            "adapter_package": self.adapter_package,
            "metadata_validation": self.metadata_validation,
            "online_smoke": self.online_smoke,
            "issue_body": self.issue_body,
        }


@dataclass(frozen=True)
class IterationPlan:
    current_version: str
    target_version: str
    recommended_theme: str
    recommended_slice: str
    readiness_ok: bool
    publication_ok: bool
    commit_days: str
    case_assets: str
    candidate_cases: list[str]
    candidate_promotions: list[CandidatePromotion]
    blockers: list[str]
    next_actions: list[str]
    validation_commands: list[str]
    candidate_issue_gate: dict[str, Any]
    publication_visibility: dict[str, str]
    publication_next_action_count: int
    publication_next_actions: list[str]
    publication_publish_command_count: int
    publication_publish_commands: list[str]
    publication_ref_context: dict[str, Any]
    publication_worktree_clean: bool
    publication_worktree_status: list[str]
    publication_publish_script_path: str
    publication_publish_script_path_sha256: str
    publication_publish_script_command: str
    publication_publish_script_command_sha256: str
    issue_artifacts_command: str
    release_draft_path: str
    release_draft_issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "target_version": self.target_version,
            "recommended_theme": self.recommended_theme,
            "recommended_slice": self.recommended_slice,
            "readiness_ok": self.readiness_ok,
            "publication_ok": self.publication_ok,
            "commit_days": self.commit_days,
            "case_assets": self.case_assets,
            "candidate_cases": self.candidate_cases,
            "candidate_promotions": [promotion.to_dict() for promotion in self.candidate_promotions],
            "blockers": self.blockers,
            "next_actions": self.next_actions,
            "validation_commands": self.validation_commands,
            "candidate_issue_gate": self.candidate_issue_gate,
            "publication_visibility": self.publication_visibility,
            "publication_next_action_count": self.publication_next_action_count,
            "publication_next_actions": self.publication_next_actions,
            "publication_publish_command_count": self.publication_publish_command_count,
            "publication_publish_commands": self.publication_publish_commands,
            "publication_ref_context": self.publication_ref_context,
            "publication_worktree_clean": self.publication_worktree_clean,
            "publication_worktree_status": self.publication_worktree_status,
            "publication_publish_script_path": self.publication_publish_script_path,
            "publication_publish_script_path_sha256": self.publication_publish_script_path_sha256,
            "publication_publish_script_command": self.publication_publish_script_command,
            "publication_publish_script_command_sha256": (
                self.publication_publish_script_command_sha256
            ),
            "issue_artifacts_command": self.issue_artifacts_command,
            "release_draft_path": self.release_draft_path,
            "release_draft_issues": self.release_draft_issues,
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


def _publication_publish_commands(publication: Any) -> list[str]:
    commands = getattr(publication, "publish_commands", None)
    if commands is not None:
        return [str(command) for command in commands]
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return []
    payload = to_dict()
    return [str(command) for command in payload.get("publish_commands", [])]


def _publication_next_actions(publication: Any) -> list[str]:
    actions = getattr(publication, "next_actions", None)
    if actions is not None:
        return [str(action).removeprefix("- ") for action in actions]
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return []
    payload = to_dict()
    return [str(action).removeprefix("- ") for action in payload.get("next_actions", [])]


def _publication_worktree_clean(publication: Any) -> bool:
    clean = getattr(publication, "worktree_clean", None)
    if clean is not None:
        return bool(clean)
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return True
    payload = to_dict()
    return bool(payload.get("worktree_clean", True))


def _publication_ref_context(publication: Any) -> dict[str, Any]:
    fields = [
        "repo_root",
        "branch",
        "upstream",
        "remote",
        "local_head",
        "upstream_head",
        "ahead_count",
        "behind_count",
        "latest_tag",
        "tag_commit",
        "tag_points_at_head",
        "tag_commit_in_upstream",
        "branch_published",
        "tag_published",
        "remote_branch_head",
        "remote_tag_commit",
        "remote_checked",
    ]
    to_dict = getattr(publication, "to_dict", None)
    payload = to_dict() if callable(to_dict) else {}
    return {field: getattr(publication, field, payload.get(field, None)) for field in fields}


def _publication_visibility(publication: Any) -> dict[str, str]:
    if not _publication_worktree_clean(publication):
        return {
            "status": "dirty_worktree",
            "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
        }
    if bool(getattr(publication, "ok", False)):
        return {
            "status": "published",
            "summary": "Latest local release branch and tag are published.",
        }

    branch = str(getattr(publication, "branch", "") or "HEAD")
    remote = str(getattr(publication, "remote", "") or "upstream")
    latest_tag = str(getattr(publication, "latest_tag", "") or "(no tag)")
    ahead_count = getattr(publication, "ahead_count", None)
    tag_published = getattr(publication, "tag_published", None)
    remote_checked = bool(getattr(publication, "remote_checked", False))

    if isinstance(ahead_count, int) and ahead_count > 0:
        return {
            "status": "local_only",
            "summary": (
                f"`{branch}` is ahead of `{remote}` by {ahead_count} commits; "
                f"publish `{branch}` and `{latest_tag}` after maintainer approval."
            ),
        }
    if tag_published is False:
        check_note = (
            "remote check confirmed the tag is missing or stale"
            if remote_checked
            else "remote check has not run yet"
        )
        return {
            "status": "tag_not_visible",
            "summary": f"`{latest_tag}` is not visible on `{remote}`; {check_note}.",
        }
    return {
        "status": "needs_remote_check",
        "summary": "Publication visibility is inconclusive; rerun with `--remote` to verify live refs.",
    }


def _candidate_issue_gate(readiness: Any, publication: Any) -> dict[str, Any]:
    release_draft_issues = _release_draft_issues(readiness)
    evidence = _candidate_issue_gate_evidence(readiness, publication)
    reason_codes = _candidate_issue_gate_reason_codes(release_draft_issues, publication)
    reason_descriptions = _candidate_issue_gate_reason_descriptions(reason_codes)
    release_draft_actions = _release_draft_required_actions(release_draft_issues)
    if not bool(getattr(publication, "ok", False)):
        publication_actions = _publication_next_actions(publication) or [
            "Run python scripts/check_release_publication.py --json and resolve publication blockers."
        ]
        actions = [*publication_actions, *release_draft_actions]
        return {
            "status": "blocked_by_publication",
            "can_create_issues": False,
            "requires_maintainer_review": True,
            "summary": "Do not create candidate issues until the latest local release is publicly visible.",
            **_candidate_issue_gate_reason_fields(reason_codes),
            "reason_descriptions": reason_descriptions,
            **_candidate_issue_gate_action_fields(actions),
            "evidence": evidence,
        }
    if release_draft_issues:
        actions = release_draft_actions
        return {
            "status": "review_required",
            "can_create_issues": True,
            "requires_maintainer_review": True,
            "summary": "Release draft issues must be resolved or intentionally deferred before tagging.",
            **_candidate_issue_gate_reason_fields(reason_codes),
            "reason_descriptions": reason_descriptions,
            **_candidate_issue_gate_action_fields(actions),
            "evidence": evidence,
        }
    actions: list[str] = []
    return {
        "status": "ready",
        "can_create_issues": True,
        "requires_maintainer_review": False,
        "summary": "Candidate issues can be created after reviewing the generated artifacts.",
        **_candidate_issue_gate_reason_fields(reason_codes),
        "reason_descriptions": reason_descriptions,
        **_candidate_issue_gate_action_fields(actions),
        "evidence": evidence,
    }


def _candidate_issue_gate_reason_fields(reason_codes: list[str]) -> dict[str, Any]:
    return {
        "reason_code_count": len(reason_codes),
        "reason_codes_sha256": _stable_json_sha256(reason_codes),
        "reason_codes": reason_codes,
    }


def _candidate_issue_gate_action_fields(actions: list[str]) -> dict[str, Any]:
    return {
        "required_action_count": len(actions),
        "required_actions_sha256": _stable_json_sha256(actions),
        "required_actions": actions,
    }


def _release_draft_required_actions(release_draft_issues: list[str]) -> list[str]:
    return [f"Resolve release draft issue: {issue}" for issue in release_draft_issues]


def _stable_json_sha256(value: object) -> str:
    digest_source = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(digest_source).hexdigest()


def _candidate_issue_gate_reason_codes(release_draft_issues: list[str], publication: Any) -> list[str]:
    codes: list[str] = []
    if not bool(getattr(publication, "ok", False)):
        codes.append("publication_not_published")
        visibility_status = _publication_visibility(publication).get("status")
        if visibility_status == "dirty_worktree":
            codes.append("dirty_worktree")
        elif visibility_status == "local_only":
            codes.append("local_release_only")
        elif visibility_status == "tag_not_visible":
            codes.append("tag_not_visible")
        elif visibility_status == "needs_remote_check":
            codes.append("needs_remote_check")
    if release_draft_issues:
        codes.append("release_draft_issues")
    return codes


def _candidate_issue_gate_reason_descriptions(reason_codes: list[str]) -> dict[str, str]:
    descriptions = {
        "publication_not_published": "The latest local release branch or tag is not visible upstream.",
        "dirty_worktree": "The working tree has uncommitted changes that must be resolved first.",
        "local_release_only": "The local branch is ahead of upstream and needs maintainer-approved publishing.",
        "tag_not_visible": "The latest local release tag is not visible on the configured remote.",
        "needs_remote_check": "Live remote refs have not been checked yet.",
        "release_draft_issues": "The target release draft still has validation issues.",
    }
    return {code: descriptions[code] for code in reason_codes if code in descriptions}


def _candidate_issue_gate_evidence(readiness: Any, publication: Any) -> dict[str, Any]:
    release_draft_issues = _release_draft_issues(readiness)
    publication_visibility = _publication_visibility(publication)
    draft = getattr(readiness, "draft", None)
    return {
        "publication_ok": bool(getattr(publication, "ok", False)),
        "publication_visibility_status": publication_visibility.get("status") or "(unknown)",
        "publication_worktree_clean": _publication_worktree_clean(publication),
        "publication_remote_checked": bool(getattr(publication, "remote_checked", False)),
        "publication_branch": str(getattr(publication, "branch", "") or "HEAD"),
        "publication_latest_tag": str(getattr(publication, "latest_tag", "") or "(none)"),
        "publication_ahead_count": getattr(publication, "ahead_count", None),
        "release_draft_ok": bool(getattr(draft, "ok", False)),
        "release_draft_path": _release_draft_evidence_path(readiness),
        "release_draft_issue_count": len(release_draft_issues),
    }


def _release_draft_evidence_path(readiness: Any) -> str:
    target_version = str(getattr(readiness, "target_version", "") or "")
    if target_version:
        return f"docs/releases/v{target_version}-draft.md"
    draft = getattr(readiness, "draft", None)
    return str(getattr(draft, "path", "") or "")


def _publication_worktree_status(publication: Any) -> list[str]:
    status = getattr(publication, "worktree_status", None)
    if status is not None:
        return [str(line) for line in status]
    to_dict = getattr(publication, "to_dict", None)
    if not callable(to_dict):
        return []
    payload = to_dict()
    return [str(line) for line in payload.get("worktree_status", [])]


def _release_draft_issues(readiness: Any) -> list[str]:
    draft = getattr(readiness, "draft", None)
    issues = getattr(draft, "issues", []) if draft is not None else []
    if not isinstance(issues, list):
        return []
    return [str(issue) for issue in issues]


def _next_action_lines(readiness: Any, publication: Any) -> list[str]:
    actions: list[str] = []
    if not publication.ok:
        if publication.ahead_count and publication.ahead_count > 0:
            actions.append(
                f"Publish the current local release: push `{publication.branch or 'HEAD'}` "
                f"and tag `{publication.latest_tag or '(none)'}` after maintainer approval."
            )
        elif publication.latest_tag and publication.tag_published is False:
            actions.append(f"Publish tag `{publication.latest_tag}` after the branch is visible upstream.")
    if readiness.blockers:
        actions.append("Clear release readiness blockers before tagging the target version.")
    if readiness.cadence.commit_day_count < readiness.cadence.min_commit_days:
        missing = readiness.cadence.min_commit_days - readiness.cadence.commit_day_count
        actions.append(f"Ship verified slices on `{missing}` more unique commit days this week.")
    if readiness.cases.candidate:
        actions.append("Promote one candidate case by collecting adapter package, metadata, and online smoke evidence.")
    actions.append(f"Draft and verify `docs/releases/v{readiness.target_version}-draft.md` for the next release.")

    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def _recommended_slice(readiness: Any, publication: Any) -> tuple[str, str]:
    if not publication.ok:
        return (
            "发布可见性",
            "先让最新本地 tag 和分支在远端可见，再继续扩大下一版范围。",
        )
    if readiness.cases.candidate:
        return (
            "真实案例库",
            "选择一个 candidate 案例，补齐 adapter_package、metadata_validation 和 online_smoke 证据。",
        )
    if readiness.blockers:
        return (
            "发布门禁",
            "优先关闭 readiness blocker，让下个 patch 可以直接进入 release preflight。",
        )
    return (
        "新用户可用性",
        "围绕 quickstart、doctor 下一步提示或案例入口提交一个可离线验证的小切片。",
    )


def _promotion_value(promotion: Any, field_name: str) -> str:
    if isinstance(promotion, dict):
        return str(promotion.get(field_name) or "")
    return str(getattr(promotion, field_name, "") or "")


def _case_string_list(case: Any, field_name: str) -> list[str]:
    value = getattr(case, field_name, None)
    if value is None and isinstance(case, dict):
        value = case.get(field_name)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _case_string_value(case: Any, field_name: str) -> str:
    value = getattr(case, field_name, None)
    if value is None and isinstance(case, dict):
        value = case.get(field_name)
    return str(value or "")


def _candidate_promotions(readiness: Any) -> list[CandidatePromotion]:
    promotions: list[CandidatePromotion] = []
    for case in readiness.cases.cases:
        if case.status != "candidate":
            continue
        promotion = getattr(case, "promotion", None)
        if promotion is None:
            continue
        promotions.append(
            CandidatePromotion(
                case_id=str(case.id),
                issue_title=_candidate_issue_title(str(case.id)),
                issue_labels=["case-proposal", "good first issue"],
                target_url=_case_string_value(case, "target_url"),
                commands=_case_string_list(case, "commands"),
                offline_commands=_case_string_list(case, "offline_commands"),
                adapter_package=_promotion_value(promotion, "adapter_package"),
                metadata_validation=_promotion_value(promotion, "metadata_validation"),
                online_smoke=_promotion_value(promotion, "online_smoke"),
                issue_body=_candidate_issue_body(
                    case_id=str(case.id),
                    target_url=_case_string_value(case, "target_url"),
                    commands=_case_string_list(case, "commands"),
                    offline_commands=_case_string_list(case, "offline_commands"),
                    adapter_package=_promotion_value(promotion, "adapter_package"),
                    metadata_validation=_promotion_value(promotion, "metadata_validation"),
                    online_smoke=_promotion_value(promotion, "online_smoke"),
                ),
            )
        )
    return promotions


def _candidate_issue_title(case_id: str) -> str:
    return f"Promote candidate case `{case_id}` toward active"


def _candidate_issue_body(
    *,
    case_id: str,
    target_url: str,
    commands: list[str],
    offline_commands: list[str],
    adapter_package: str,
    metadata_validation: str,
    online_smoke: str,
) -> str:
    command_lines = [f"  - `{command}`" for command in commands] or ["  - Not declared."]
    offline_command_lines = [f"  - `{command}`" for command in offline_commands] or ["  - Not declared."]
    return "\n".join(
        [
            f"## Scope: promote candidate case `{case_id}`",
            "",
            "Move this candidate case one step closer to `active` without changing its status early.",
            "",
            "## Reproduction Context",
            f"- Target URL: {target_url or 'Not declared.'}",
            "- Candidate commands:",
            *command_lines,
            "- Offline validation commands:",
            *offline_command_lines,
            "",
            "## Tasks",
            f"- [ ] `adapter_package`: {adapter_package}",
            f"- [ ] `metadata_validation`: {metadata_validation}",
            f"- [ ] `online_smoke`: {online_smoke}",
            "",
            "## Validation Evidence",
            "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.",
            "- Paste the local `scripts/validate_cases.py --packages-dir` result.",
            "- Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`.",
            "",
            "## Non-goals",
            "- Do not mark the case `active` until all three promotion tasks are complete.",
            "- Do not require real LLM keys or write runtime state into the repository.",
        ]
    )


def build_plan(
    root: Path = ROOT,
    *,
    today: date | None = None,
    target_version: str | None = None,
    min_commit_days: int = 3,
    min_case_assets: int = 8,
    readiness_report: Any | None = None,
    publication_report: Any | None = None,
) -> IterationPlan:
    current_version = _project_version(root)
    expected_target = target_version or _next_patch_version(current_version)
    readiness = readiness_report or build_readiness_report(
        root,
        today=today or date.today(),
        min_commit_days=min_commit_days,
        min_case_assets=min_case_assets,
        target_version=expected_target,
    )
    publication = publication_report or build_publication_report(root)
    theme, release_slice = _recommended_slice(readiness, publication)
    candidate_promotions = _candidate_promotions(readiness)
    publication_next_actions = _publication_next_actions(publication)
    publication_publish_commands = _publication_publish_commands(publication)
    candidate_cases = [
        str(case.id)
        for case in readiness.cases.cases
        if case.status == "candidate"
    ]
    blockers = [*readiness.blockers]
    if not publication.ok:
        blockers.append("latest local release is not published")

    validation_commands = [
        f"python scripts/plan_next_iteration.py --target-version {readiness.target_version} --json",
        f"python scripts/release_readiness.py --target-version {readiness.target_version} --json",
        "python scripts/check_release_publication.py --json",
        "python scripts/validate_cases.py --strict",
    ]
    issue_artifacts_command = (
        f"python scripts/plan_next_iteration.py --target-version {readiness.target_version} "
        "--issues-dir /tmp/cliany-candidate-issues"
    )
    publication_publish_script_command = (
        "python scripts/check_release_publication.py --json "
        f"--publish-script {PUBLICATION_PUBLISH_SCRIPT_PATH}"
    )
    return IterationPlan(
        current_version=current_version,
        target_version=str(readiness.target_version),
        recommended_theme=theme,
        recommended_slice=release_slice,
        readiness_ok=bool(readiness.ok),
        publication_ok=bool(publication.ok),
        commit_days=f"{readiness.cadence.commit_day_count}/{readiness.cadence.min_commit_days}",
        case_assets=(
            f"active {readiness.cases.active}, candidate {readiness.cases.candidate}, "
            f"known_gap {readiness.cases.known_gap}, total {readiness.cases.total}/{readiness.min_case_assets}"
        ),
        candidate_cases=candidate_cases,
        candidate_promotions=candidate_promotions,
        blockers=blockers,
        next_actions=_next_action_lines(readiness, publication),
        validation_commands=validation_commands,
        candidate_issue_gate=_candidate_issue_gate(readiness, publication),
        publication_visibility=_publication_visibility(publication),
        publication_next_action_count=len(publication_next_actions),
        publication_next_actions=publication_next_actions,
        publication_publish_command_count=len(publication_publish_commands),
        publication_publish_commands=publication_publish_commands,
        publication_ref_context=_publication_ref_context(publication),
        publication_worktree_clean=_publication_worktree_clean(publication),
        publication_worktree_status=_publication_worktree_status(publication),
        publication_publish_script_path=PUBLICATION_PUBLISH_SCRIPT_PATH,
        publication_publish_script_path_sha256=_stable_json_sha256(PUBLICATION_PUBLISH_SCRIPT_PATH),
        publication_publish_script_command=publication_publish_script_command,
        publication_publish_script_command_sha256=_stable_json_sha256(
            publication_publish_script_command
        ),
        issue_artifacts_command=issue_artifacts_command,
        release_draft_path=f"docs/releases/v{readiness.target_version}-draft.md",
        release_draft_issues=_release_draft_issues(readiness),
    )


def _print_text(plan: IterationPlan) -> None:
    print("=== cliany-site next iteration plan ===")
    print(f"current_version: {plan.current_version}")
    print(f"target_version: {plan.target_version}")
    print(f"recommended_theme: {plan.recommended_theme}")
    print(f"recommended_slice: {plan.recommended_slice}")
    print(f"readiness_ok: {plan.readiness_ok}")
    print(f"publication_ok: {plan.publication_ok}")
    print(f"commit_days: {plan.commit_days}")
    print(f"case_assets: {plan.case_assets}")
    print(f"release_draft_path: {plan.release_draft_path}")
    if plan.release_draft_issues:
        print("release_draft_issues:")
        for issue in plan.release_draft_issues:
            print(f"- {issue}")
    if plan.candidate_cases:
        print("candidate_cases:")
        for case_id in plan.candidate_cases:
            print(f"- {case_id}")
    if plan.candidate_promotions:
        print("candidate_promotions:")
        for promotion in plan.candidate_promotions:
            print(f"- {promotion.case_id}")
            print(f"  issue_title: {promotion.issue_title}")
            print(f"  issue_labels: {', '.join(promotion.issue_labels)}")
            print(f"  adapter_package: {promotion.adapter_package}")
            print(f"  metadata_validation: {promotion.metadata_validation}")
            print(f"  online_smoke: {promotion.online_smoke}")
            print("  issue_body:")
            for line in promotion.issue_body.splitlines():
                print(f"    {line}")
    if plan.blockers:
        print("blockers:")
        for blocker in plan.blockers:
            print(f"- {blocker}")
    print("next_actions:")
    for action in plan.next_actions:
        print(f"- {action}")
    print("validation_commands:")
    for command in plan.validation_commands:
        print(f"- {command}")
    print("candidate_issue_gate:")
    for key, value in plan.candidate_issue_gate.items():
        _print_text_item(key, value)
    print("publication_visibility:")
    for key, value in plan.publication_visibility.items():
        print(f"- {key}: {value}")
    print(f"publication_next_action_count: {plan.publication_next_action_count}")
    if plan.publication_next_actions:
        print("publication_next_actions:")
        for action in plan.publication_next_actions:
            print(f"- {action}")
    print(f"publication_publish_command_count: {plan.publication_publish_command_count}")
    if plan.publication_publish_commands:
        print("publication_publish_commands:")
        for command in plan.publication_publish_commands:
            print(f"- {command}")
    print("publication_ref_context:")
    for key, value in plan.publication_ref_context.items():
        print(f"- {key}: {value}")
    print(f"publication_worktree_clean: {str(plan.publication_worktree_clean).lower()}")
    if plan.publication_worktree_status:
        print("publication_worktree_status:")
        for line in plan.publication_worktree_status:
            print(f"- {line}")
    print(f"publication_publish_script_path: {plan.publication_publish_script_path}")
    print(f"publication_publish_script_path_sha256: {plan.publication_publish_script_path_sha256}")
    print(f"publication_publish_script_command: {plan.publication_publish_script_command}")
    print(
        "publication_publish_script_command_sha256: "
        f"{plan.publication_publish_script_command_sha256}"
    )
    print(f"issue_artifacts_command: {plan.issue_artifacts_command}")


def _print_text_item(key: str, value: object) -> None:
    if isinstance(value, list):
        print(f"- {key}:")
        for item in value:
            print(f"  - {item}")
        return
    if isinstance(value, dict):
        print(f"- {key}:")
        for nested_key, nested_value in value.items():
            print(f"  - {nested_key}: {_format_context_value(nested_value)}")
        return
    print(f"- {key}: {value}")


def _render_markdown(plan: IterationPlan) -> str:
    candidate_cases = ", ".join(f"`{case_id}`" for case_id in plan.candidate_cases) or "-"
    blockers = "\n".join(f"- {blocker}" for blocker in plan.blockers) or "- None."
    next_actions = "\n".join(f"- {action}" for action in plan.next_actions)
    validation = "\n".join(f"- `{command}`" for command in plan.validation_commands)
    publication_visibility = _publication_visibility_markdown(plan.publication_visibility)
    candidate_issue_gate = _candidate_issue_gate_markdown(plan.candidate_issue_gate)
    publication_actions = _publication_next_actions_markdown(plan.publication_next_actions)
    publication_refs = _publication_ref_context_markdown(plan.publication_ref_context)
    publication_worktree = _publication_worktree_markdown(
        plan.publication_worktree_clean,
        plan.publication_worktree_status,
    )
    publication_commands = _publication_commands_markdown(plan.publication_publish_commands)
    publication_script = _publication_script_markdown(
        plan.publication_publish_script_path,
        plan.publication_publish_script_command,
    )
    promotion_lines = _candidate_promotion_markdown(plan.candidate_promotions)
    release_draft_issues = _release_draft_issues_markdown(plan.release_draft_issues)
    return f"""# cliany-site Next Iteration Plan

| Metric | Value |
|--------|-------|
| current_version | `{plan.current_version}` |
| target_version | `{plan.target_version}` |
| recommended_theme | {plan.recommended_theme} |
| readiness_ok | `{str(plan.readiness_ok).lower()}` |
| publication_ok | `{str(plan.publication_ok).lower()}` |
| publication_next_action_count | `{plan.publication_next_action_count}` |
| publication_publish_command_count | `{plan.publication_publish_command_count}` |
| publication_publish_script_path | `{plan.publication_publish_script_path}` |
| publication_publish_script_path_sha256 | `{plan.publication_publish_script_path_sha256}` |
| publication_publish_script_command_sha256 | `{plan.publication_publish_script_command_sha256}` |
| commit_days | `{plan.commit_days}` |
| case_assets | {plan.case_assets} |
| candidate_cases | {candidate_cases} |

## Recommended Slice

{plan.recommended_slice}

## Blockers

{blockers}

## Next Actions

{next_actions}

{promotion_lines}

## Validation Commands

{validation}

{publication_visibility}

{candidate_issue_gate}

{publication_actions}

{publication_refs}

{publication_worktree}

{publication_commands}

{publication_script}

## Release Draft

- `{plan.release_draft_path}`
{release_draft_issues}
"""


def _release_draft_issues_markdown(issues: list[str]) -> str:
    if not issues:
        return ""
    issue_lines = "\n".join(f"- {issue}" for issue in issues)
    return f"\n\n### Release Draft Issues\n\n{issue_lines}"


def _publication_next_actions_markdown(actions: list[str]) -> str:
    if not actions:
        return "## Publication Next Actions\n\n- No publication next actions are needed."
    action_lines = "\n".join(f"- {action}" for action in actions)
    return f"""## Publication Next Actions

{action_lines}"""


def _candidate_issue_gate_markdown(gate: dict[str, Any]) -> str:
    status = gate.get("status") or "(unknown)"
    can_create = str(bool(gate.get("can_create_issues", False))).lower()
    review_required = str(bool(gate.get("requires_maintainer_review", True))).lower()
    summary = gate.get("summary") or "Candidate issue gate has not been summarized."
    reason_count = gate.get("reason_code_count")
    reason_hash = gate.get("reason_codes_sha256") or "(unknown)"
    action_count = gate.get("required_action_count")
    action_hash = gate.get("required_actions_sha256") or "(unknown)"
    reason_codes = gate.get("reason_codes")
    reason_descriptions = gate.get("reason_descriptions")
    actions = gate.get("required_actions")
    evidence = gate.get("evidence")
    if not isinstance(reason_codes, list) or not reason_codes:
        reason_lines = "- No candidate issue gate reason codes are reported."
    else:
        reason_lines = "\n".join(f"- `{reason}`" for reason in reason_codes)
    description_lines = _candidate_issue_gate_reason_descriptions_markdown(reason_descriptions)
    if not isinstance(actions, list) or not actions:
        action_lines = "- No required actions are reported."
    else:
        action_lines = "\n".join(f"- {action}" for action in actions)
    evidence_lines = _candidate_issue_gate_evidence_markdown(evidence)
    return f"""## Candidate Issue Gate

- status: `{status}`
- can_create_issues: `{can_create}`
- requires_maintainer_review: `{review_required}`
- summary: {summary}
- reason_code_count: `{_format_context_value(reason_count)}`
- reason_codes_sha256: `{_format_context_value(reason_hash)}`
- required_action_count: `{_format_context_value(action_count)}`
- required_actions_sha256: `{_format_context_value(action_hash)}`

### Candidate Issue Gate Reason Codes

{reason_lines}

### Candidate Issue Gate Reason Descriptions

{description_lines}

### Candidate Issue Gate Evidence

{evidence_lines}

### Candidate Issue Gate Actions

{action_lines}"""


def _candidate_issue_gate_evidence_markdown(evidence: object) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return "- No candidate issue gate evidence is reported."
    rows = [
        ("publication_ok", evidence.get("publication_ok")),
        ("publication_visibility_status", evidence.get("publication_visibility_status")),
        ("publication_worktree_clean", evidence.get("publication_worktree_clean")),
        ("publication_remote_checked", evidence.get("publication_remote_checked")),
        ("publication_branch", evidence.get("publication_branch")),
        ("publication_latest_tag", evidence.get("publication_latest_tag")),
        ("publication_ahead_count", evidence.get("publication_ahead_count")),
        ("release_draft_ok", evidence.get("release_draft_ok")),
        ("release_draft_path", evidence.get("release_draft_path")),
        ("release_draft_issue_count", evidence.get("release_draft_issue_count")),
    ]
    lines = ["| Field | Value |", "|-------|-------|"]
    lines.extend(f"| {key} | `{_format_context_value(value)}` |" for key, value in rows)
    return "\n".join(lines)


def _publication_visibility_markdown(visibility: dict[str, str]) -> str:
    status = visibility.get("status") or "(unknown)"
    summary = visibility.get("summary") or "Publication visibility has not been summarized."
    return f"""## Publication Visibility

- status: `{status}`
- summary: {summary}"""


def _publication_script_markdown(path: str, command: str) -> str:
    return f"""## Publication Publish Script

- path: `{path}`

```bash
{command}
```"""


def _publication_worktree_markdown(clean: bool, status: list[str]) -> str:
    if clean:
        return "## Publication Worktree\n\n- worktree_clean: `true`"
    status_lines = "\n".join(status) or "(no status lines)"
    return f"""## Publication Worktree

- worktree_clean: `false`

```text
{status_lines}
```"""


def _publication_ref_context_markdown(context: dict[str, Any]) -> str:
    rows = [
        ("repo_root", context.get("repo_root")),
        ("branch", context.get("branch")),
        ("upstream", context.get("upstream")),
        ("remote", context.get("remote")),
        ("latest_tag", context.get("latest_tag")),
        ("local_head", context.get("local_head")),
        ("tag_commit", context.get("tag_commit")),
        ("ahead_count", context.get("ahead_count")),
        ("behind_count", context.get("behind_count")),
        ("remote_checked", context.get("remote_checked")),
    ]
    lines = ["## Publication Ref Context", "", "| Field | Value |", "|-------|-------|"]
    lines.extend(f"| {key} | `{_format_context_value(value)}` |" for key, value in rows)
    return "\n".join(lines)


def _format_context_value(value: object) -> str:
    if value is None:
        return "(none)"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _publication_commands_markdown(commands: list[str]) -> str:
    if not commands:
        return "## Publication Publish Commands\n\n- No publication publish commands are needed."
    command_lines = "\n".join(commands)
    return f"""## Publication Publish Commands

```bash
{command_lines}
```"""


def _candidate_promotion_markdown(promotions: list[CandidatePromotion]) -> str:
    if not promotions:
        return (
            "## Candidate Issue Metadata\n\n"
            "- No candidate issue metadata is available.\n\n"
            "## Candidate Promotion Tasks\n\n"
            "- No candidate promotion tasks are available."
        )

    lines = [
        "## Candidate Issue Metadata",
        "",
        "| Case | Issue Title | Labels |",
        "|------|-------------|--------|",
    ]
    for promotion in promotions:
        labels = ", ".join(f"`{label}`" for label in promotion.issue_labels)
        lines.append(f"| `{promotion.case_id}` | {promotion.issue_title} | {labels} |")

    lines.extend(
        [
            "",
            "## Candidate Promotion Tasks",
            "",
            "| Case | Adapter Package | Metadata Validation | Online Smoke |",
            "|------|-----------------|---------------------|--------------|",
        ]
    )
    for promotion in promotions:
        lines.append(
            f"| `{promotion.case_id}` | {promotion.adapter_package} | "
            f"{promotion.metadata_validation} | {promotion.online_smoke} |"
        )
    lines.extend(["", "## Candidate Issue Body Templates"])
    for promotion in promotions:
        lines.extend(
            [
                "",
                f"### `{promotion.case_id}`",
                "",
                "```markdown",
                promotion.issue_body,
                "```",
            ]
        )
    return "\n".join(lines)


def _write_markdown_report(plan: IterationPlan, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(plan), encoding="utf-8")


def _write_candidate_issue_files(plan: IterationPlan, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    metadata: list[dict[str, Any]] = []
    issue_commands: list[str] = []
    issue_body_inventory = _issue_body_inventory(plan.candidate_promotions)
    issue_body_summary = _issue_body_summary(issue_body_inventory)
    for promotion in plan.candidate_promotions:
        body_path = directory / f"{promotion.case_id}.md"
        body_path.write_text(promotion.issue_body + "\n", encoding="utf-8")
        labels = [*promotion.issue_labels]
        create_command = _gh_issue_create_command(promotion, body_path)
        metadata.append(
            {
                "case_id": promotion.case_id,
                "issue_title": promotion.issue_title,
                "issue_labels": labels,
                "target_url": promotion.target_url,
                "commands": promotion.commands,
                "offline_commands": promotion.offline_commands,
                "issue_body_name": body_path.name,
                "issue_body_file": str(body_path),
                "create_command": create_command,
            }
        )
        issue_commands.append(create_command)

    issue_body_names = [f"{promotion.case_id}.md" for promotion in plan.candidate_promotions]
    candidate_cases = [promotion.case_id for promotion in plan.candidate_promotions]
    script_path = directory / "create-issues.sh"
    create_issues_safety = _issue_artifact_create_issues_safety(script_path)
    artifact_files = _issue_artifact_files(issue_body_names)
    review_order = [
        "README.md",
        "publication-handoff.json",
        "release-draft-handoff.json",
        "issue-metadata.json",
        *issue_body_names,
        "create-issues.sh",
    ]
    artifact_bundle_summary = _issue_artifact_bundle_summary(
        plan=plan,
        candidate_cases=candidate_cases,
        review_order=review_order,
        issue_body_summary=issue_body_summary,
        issue_metadata_summary=_issue_metadata_summary(metadata),
        create_issues_safety=create_issues_safety,
        artifact_files=artifact_files,
    )
    artifact_manifest = {
        "schema_version": 1,
        "target_version": plan.target_version,
        "artifact_bundle_summary": artifact_bundle_summary,
        "candidate_count": len(candidate_cases),
        "candidate_cases": candidate_cases,
        "blockers": plan.blockers,
        "next_actions": plan.next_actions,
        "candidate_issue_gate": plan.candidate_issue_gate,
        "publication_ok": plan.publication_ok,
        "publication_visibility": plan.publication_visibility,
        "publication_next_actions": plan.publication_next_actions,
        "publication_publish_commands": plan.publication_publish_commands,
        "publication_ref_context": plan.publication_ref_context,
        "publication_worktree_clean": plan.publication_worktree_clean,
        "publication_worktree_status": plan.publication_worktree_status,
        "publication_publish_script_path": plan.publication_publish_script_path,
        "publication_publish_script_path_sha256": plan.publication_publish_script_path_sha256,
        "publication_publish_script_command": plan.publication_publish_script_command,
        "publication_publish_script_command_sha256": (
            plan.publication_publish_script_command_sha256
        ),
        "release_draft_path": plan.release_draft_path,
        "release_draft_issues": plan.release_draft_issues,
        "issue_artifacts_command": plan.issue_artifacts_command,
        "create_issues_dry_run_command": create_issues_safety["dry_run_command"],
        "create_issues_safety": create_issues_safety,
        "issue_body_inventory": issue_body_inventory,
        "issue_body_summary": issue_body_summary,
        "issue_metadata_summary": _issue_metadata_summary(metadata),
        "files": artifact_files,
        "review_order": review_order,
        "review_checklist": _issue_artifact_review_checklist(),
        "validation_commands": _issue_artifact_validation_commands(plan),
    }
    (directory / "artifact-manifest.json").write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / "issue-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    publication_handoff = _publication_handoff(plan)
    (directory / "publication-handoff.json").write_text(
        json.dumps(publication_handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    release_draft_handoff = _release_draft_handoff(plan)
    (directory / "release-draft-handoff.json").write_text(
        json.dumps(release_draft_handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    script_path.write_text("\n".join(_candidate_issue_script_lines(issue_commands)) + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    (directory / "README.md").write_text(_render_issue_artifacts_readme(plan), encoding="utf-8")


def _candidate_issue_script_lines(issue_commands: list[str]) -> list[str]:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Review these commands before running; they create GitHub issues in the current repository.",
        "# Set CLIANY_CREATE_ISSUES_DRY_RUN=1 to print commands without running the preflight or gh.",
        "# Stop early if the latest local release is not publicly visible yet.",
        'REPO_ROOT="$(git rev-parse --show-toplevel)"',
        'cd "$REPO_ROOT"',
        'if [[ "${CLIANY_CREATE_ISSUES_DRY_RUN:-0}" == "1" ]]; then',
        '  echo "Dry run: publication preflight and gh issue create are not executed."',
        "  cat <<'CLIANY_ISSUE_COMMANDS'",
    ]
    lines.extend(issue_commands)
    lines.extend(
        [
            "CLIANY_ISSUE_COMMANDS",
            "  exit 0",
            "fi",
            'PREFLIGHT_JSON="/tmp/cliany-issue-publication-check.json"',
            'if ! python scripts/check_release_publication.py --strict --json >"$PREFLIGHT_JSON"; then',
            '  echo "Release publication preflight failed; review $PREFLIGHT_JSON '
            'before creating candidate issues." >&2',
            '  cat "$PREFLIGHT_JSON" >&2',
            "  exit 1",
            "fi",
        ]
    )
    lines.extend(f"\n{command}" for command in issue_commands)
    return lines


def _render_issue_artifacts_readme(plan: IterationPlan) -> str:
    body_files = "\n".join(f"- `{promotion.case_id}.md`" for promotion in plan.candidate_promotions)
    body_files = body_files or "- No candidate issue body files were generated."
    candidate_summary = _issue_artifact_candidate_summary(plan.candidate_promotions)
    body_inventory = _issue_artifact_body_inventory_markdown(plan.candidate_promotions)
    body_summary = _issue_artifact_body_summary_markdown(plan.candidate_promotions)
    gate_quick_summary = _issue_artifact_gate_quick_summary(plan)
    bundle_summary = _issue_artifact_bundle_summary_markdown(plan)
    gate_reason_codes = _issue_artifact_gate_reason_codes(plan)
    gate_reason_descriptions = _issue_artifact_gate_reason_descriptions(plan)
    gate_latest_tag = _format_context_value(_candidate_issue_gate_evidence_value(plan, "publication_latest_tag"))
    gate_ahead_count = _format_context_value(_candidate_issue_gate_evidence_value(plan, "publication_ahead_count"))
    gate_worktree_clean = _format_context_value(
        _candidate_issue_gate_evidence_value(plan, "publication_worktree_clean")
    )
    gate_draft_ok = _format_context_value(_candidate_issue_gate_evidence_value(plan, "release_draft_ok"))
    gate_draft_issues = _format_context_value(_candidate_issue_gate_evidence_value(plan, "release_draft_issue_count"))
    create_issues_safety = _issue_artifact_create_issues_safety(Path("create-issues.sh"))
    return f"""# cliany-site Candidate Issue Artifacts

Generated for target version `{plan.target_version}`.

## Files

- `issue-metadata.json`: structured issue title, labels, reproduction context, body file name,
  body file path, and `gh issue create` command.
- `artifact-manifest.json`: schema version, candidate cases, blockers, next actions, file names, review order,
  review checklist, candidate issue gate, publication status, publication ref context, worktree status,
  release draft handoff, reproduction command, publish commands, and validation commands for this candidate
  issue artifact bundle.
- `publication-handoff.json`: publication status, candidate issue gate, visibility, next actions,
  publication next actions, ref context, worktree status, and publish commands to review first.
- `release-draft-handoff.json`: target version, release draft path, and release draft issues
  to review before tagging the target version.
- `create-issues.sh`: reviewable shell script with a release publication preflight and
  one `gh issue create` command per candidate. Set `CLIANY_CREATE_ISSUES_DRY_RUN=1`
  to print the commands without running the preflight or creating issues.
{body_files}

{candidate_summary}

{body_inventory}

{body_summary}

{gate_quick_summary}

{bundle_summary}

## Publication Handoff

- publication_ok: `{str(plan.publication_ok).lower()}`
- candidate_issue_gate: `{_format_context_value(plan.candidate_issue_gate.get("status"))}`
- can_create_issues: `{str(bool(plan.candidate_issue_gate.get("can_create_issues", False))).lower()}`
- gate_summary: {_format_context_value(plan.candidate_issue_gate.get("summary"))}
- gate_reason_code_count: `{_format_context_value(plan.candidate_issue_gate.get("reason_code_count"))}`
- gate_reason_codes_sha256: `{_format_context_value(plan.candidate_issue_gate.get("reason_codes_sha256"))}`
- gate_required_action_count: `{_format_context_value(plan.candidate_issue_gate.get("required_action_count"))}`
- gate_required_actions_sha256: `{_format_context_value(plan.candidate_issue_gate.get("required_actions_sha256"))}`
- gate_reason_codes: {gate_reason_codes}
- gate_reason_descriptions: {gate_reason_descriptions}
- gate_evidence_latest_tag: `{gate_latest_tag}`
- gate_evidence_ahead_count: `{gate_ahead_count}`
- gate_evidence_worktree_clean: `{gate_worktree_clean}`
- gate_evidence_release_draft_ok: `{gate_draft_ok}`
- gate_evidence_release_draft_issues: `{gate_draft_issues}`
- visibility: `{_format_context_value(plan.publication_visibility.get("status"))}`
- visibility_summary: {_format_context_value(plan.publication_visibility.get("summary"))}
- latest_tag: `{_format_context_value(plan.publication_ref_context.get("latest_tag"))}`
- local_head: `{_format_context_value(plan.publication_ref_context.get("local_head"))}`
- worktree_clean: `{str(plan.publication_worktree_clean).lower()}`
- publish_script_path: `{plan.publication_publish_script_path}`
- publish_script_path_sha256: `{plan.publication_publish_script_path_sha256}`
- publish_script_command_sha256: `{plan.publication_publish_script_command_sha256}`
- Review `publication-handoff.json` before running `create-issues.sh`.

### Publication Next Actions

{_issue_artifact_publication_next_actions(plan)}

### Publication Publish Script

- path: `{plan.publication_publish_script_path}`

```bash
{plan.publication_publish_script_command}
```

```bash
{_issue_artifact_publication_commands(plan)}
```

## Release Draft Handoff

- release_draft_path: `{plan.release_draft_path}`
- release_draft_issues:
{_issue_artifact_release_draft_issues(plan)}

## Review Checklist

{_issue_artifact_review_checklist_markdown()}

## Validation Commands

```bash
{_issue_artifact_validation_commands_text(plan)}
```

## Create Issues

`create-issues.sh` is generated for review. It is not executed by `plan_next_iteration.py`.
Run it only after checking `issue-metadata.json` and the body files. The script runs
`python scripts/check_release_publication.py --strict --json` before creating issues and
writes the preflight JSON to `/tmp/cliany-issue-publication-check.json`. If the preflight
fails, it prints that JSON before exiting.

### Create Issues Safety

- dry_run_supported: `{str(create_issues_safety["dry_run_supported"]).lower()}`
- dry_run_env: `{create_issues_safety["dry_run_env"]}`
- dry_run_command: `{create_issues_safety["dry_run_command"]}`
- preflight_required: `{str(create_issues_safety["preflight_required"]).lower()}`
- preflight_command: `{create_issues_safety["preflight_command"]}`
- preflight_json: `{create_issues_safety["preflight_json"]}`

Preview the issue commands without running the publication preflight or creating issues:

```bash
CLIANY_CREATE_ISSUES_DRY_RUN=1 ./create-issues.sh
```
"""


def _issue_artifact_gate_quick_summary(plan: IterationPlan) -> str:
    reason_codes = plan.candidate_issue_gate.get("reason_codes")
    if not isinstance(reason_codes, list):
        reason_codes = []
    reason_descriptions = plan.candidate_issue_gate.get("reason_descriptions")
    if not isinstance(reason_descriptions, dict):
        reason_descriptions = {}
    required_actions = plan.candidate_issue_gate.get("required_actions")
    if not isinstance(required_actions, list):
        required_actions = []
    primary_reason_code = reason_codes[0] if reason_codes else None
    primary_reason_description = None
    if primary_reason_code is not None:
        primary_reason_description = reason_descriptions.get(primary_reason_code)
    primary_required_action = required_actions[0] if required_actions else None
    return "\n".join(
        [
            "## Candidate Issue Gate Quick Summary",
            "",
            f"- status: `{_format_context_value(plan.candidate_issue_gate.get('status'))}`",
            "- can_create_issues: "
            f"`{str(bool(plan.candidate_issue_gate.get('can_create_issues', False))).lower()}`",
            "- requires_maintainer_review: "
            f"`{str(bool(plan.candidate_issue_gate.get('requires_maintainer_review', False))).lower()}`",
            f"- publication_ok: `{str(plan.publication_ok).lower()}`",
            f"- release_draft_ok: `{str(not plan.release_draft_issues).lower()}`",
            f"- blocker_count: `{len(plan.blockers)}`",
            f"- next_action_count: `{len(plan.next_actions)}`",
            f"- publication_next_action_count: `{plan.publication_next_action_count}`",
            f"- publication_publish_command_count: `{plan.publication_publish_command_count}`",
            "- publication_publish_script_path: "
            f"{_summary_inline_code(plan.publication_publish_script_path)}",
            "- publication_publish_script_path_sha256: "
            f"`{plan.publication_publish_script_path_sha256}`",
            "- publication_publish_script_command: "
            f"{_summary_inline_code(plan.publication_publish_script_command)}",
            "- publication_publish_script_command_sha256: "
            f"`{plan.publication_publish_script_command_sha256}`",
            "- reason_code_count: "
            f"`{_format_context_value(plan.candidate_issue_gate.get('reason_code_count'))}`",
            "- required_action_count: "
            f"`{_format_context_value(plan.candidate_issue_gate.get('required_action_count'))}`",
            f"- primary_reason_code: {_summary_inline_code(primary_reason_code)}",
            f"- primary_reason_description: {_summary_inline_code(primary_reason_description)}",
            f"- primary_required_action: {_summary_inline_code(primary_required_action)}",
            "- latest_tag: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_latest_tag'))}`",
            "- publication_branch: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_branch'))}`",
            "- publication_upstream: "
            f"`{_format_context_value(plan.publication_ref_context.get('upstream'))}`",
            "- publication_remote: "
            f"`{_format_context_value(plan.publication_ref_context.get('remote'))}`",
            "- publication_local_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('local_head'))}`",
            "- publication_tag_commit: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_commit'))}`",
            "- publication_upstream_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('upstream_head'))}`",
            "- publication_tag_points_at_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_points_at_head'))}`",
            "- publication_tag_commit_in_upstream: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_commit_in_upstream'))}`",
            "- publication_branch_published: "
            f"`{_format_context_value(plan.publication_ref_context.get('branch_published'))}`",
            "- publication_tag_published: "
            f"`{_format_context_value(plan.publication_ref_context.get('tag_published'))}`",
            "- publication_remote_branch_head: "
            f"`{_format_context_value(plan.publication_ref_context.get('remote_branch_head'))}`",
            "- publication_remote_tag_commit: "
            f"`{_format_context_value(plan.publication_ref_context.get('remote_tag_commit'))}`",
            "- publication_worktree_clean: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_worktree_clean'))}`",
            "- publication_ahead_count: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_ahead_count'))}`",
            "- publication_behind_count: "
            f"`{_format_context_value(plan.publication_ref_context.get('behind_count'))}`",
            "- publication_remote_checked: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'publication_remote_checked'))}`",
            "- release_draft_issue_count: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'release_draft_issue_count'))}`",
            "- release_draft_path: "
            f"`{_format_context_value(_candidate_issue_gate_evidence_value(plan, 'release_draft_path'))}`",
            f"- visibility: `{_format_context_value(plan.publication_visibility.get('status'))}`",
            f"- visibility_summary: {_summary_inline_code(plan.publication_visibility.get('summary'))}",
        ]
    )


def _candidate_issue_gate_evidence_value(plan: IterationPlan, key: str) -> object:
    evidence = plan.candidate_issue_gate.get("evidence")
    if not isinstance(evidence, dict):
        return None
    return evidence.get(key)


def _issue_artifact_gate_reason_codes(plan: IterationPlan) -> str:
    reason_codes = plan.candidate_issue_gate.get("reason_codes")
    if not isinstance(reason_codes, list) or not reason_codes:
        return "`(none)`"
    return ", ".join(f"`{reason}`" for reason in reason_codes)


def _candidate_issue_gate_reason_descriptions_markdown(descriptions: object) -> str:
    if not isinstance(descriptions, dict) or not descriptions:
        return "- No candidate issue gate reason descriptions are reported."
    lines = ["| Code | Description |", "|------|-------------|"]
    lines.extend(f"| `{code}` | {description} |" for code, description in descriptions.items())
    return "\n".join(lines)


def _issue_artifact_gate_reason_descriptions(plan: IterationPlan) -> str:
    descriptions = plan.candidate_issue_gate.get("reason_descriptions")
    if not isinstance(descriptions, dict) or not descriptions:
        return "`(none)`"
    return "; ".join(f"`{code}`: {description}" for code, description in descriptions.items())


def _issue_artifact_release_draft_issues(plan: IterationPlan) -> str:
    if not plan.release_draft_issues:
        return "  - No release draft issues are reported."
    return "\n".join(f"  - {issue}" for issue in plan.release_draft_issues)


def _issue_artifact_review_checklist() -> list[str]:
    return [
        "Confirm the latest local release has been published before creating new candidate work.",
        "Confirm release draft issues are resolved or intentionally deferred before tagging the target version.",
        "Confirm Publication Next Actions are resolved or intentionally deferred before running create-issues.sh.",
        (
            "Confirm issue-metadata.json has the expected target URL, candidate commands, "
            "and offline validation commands for each case."
        ),
        "Review each body file for scope, tasks, validation evidence, and non-goals.",
        (
            "Keep cases as candidate until adapter package, metadata validation, "
            "and online smoke evidence are complete."
        ),
        "Do not use real LLM keys or write runtime state into the repository.",
    ]


def _issue_artifact_review_checklist_markdown() -> str:
    return "\n".join(f"- {item}" for item in _issue_artifact_review_checklist())


def _issue_artifact_publication_commands(plan: IterationPlan) -> str:
    if plan.publication_publish_commands:
        return "\n".join(plan.publication_publish_commands)
    return "python scripts/check_release_publication.py --json"


def _issue_artifact_publication_next_actions(plan: IterationPlan) -> str:
    if not plan.publication_next_actions:
        return "- No publication next actions are needed."
    return "\n".join(f"- {action}" for action in plan.publication_next_actions)


def _issue_artifact_validation_commands(plan: IterationPlan) -> list[str]:
    return [
        plan.issue_artifacts_command,
        f"python scripts/plan_next_iteration.py --target-version {plan.target_version} --json",
        f"python scripts/release_readiness.py --target-version {plan.target_version} --json",
        "python scripts/check_release_publication.py --json",
        "python scripts/validate_cases.py --strict",
    ]


def _issue_artifact_validation_commands_text(plan: IterationPlan) -> str:
    return "\n".join(_issue_artifact_validation_commands(plan))


def _issue_artifact_create_issues_safety(script_path: Path) -> dict[str, Any]:
    return {
        "script": str(script_path),
        "dry_run_supported": True,
        "dry_run_env": "CLIANY_CREATE_ISSUES_DRY_RUN=1",
        "dry_run_command": f"CLIANY_CREATE_ISSUES_DRY_RUN=1 {script_path}",
        "preflight_required": True,
        "preflight_command": "python scripts/check_release_publication.py --strict --json",
        "preflight_json": "/tmp/cliany-issue-publication-check.json",
    }


def _issue_artifact_create_issues_safety_contract(create_issues_safety: dict[str, Any]) -> dict[str, Any]:
    return {
        "dry_run_supported": create_issues_safety["dry_run_supported"],
        "dry_run_env": create_issues_safety["dry_run_env"],
        "preflight_required": create_issues_safety["preflight_required"],
        "preflight_command": create_issues_safety["preflight_command"],
        "preflight_json": create_issues_safety["preflight_json"],
    }


def _issue_artifact_files(issue_body_names: list[str]) -> dict[str, Any]:
    return {
        "readme": "README.md",
        "issue_metadata": "issue-metadata.json",
        "publication_handoff": "publication-handoff.json",
        "release_draft_handoff": "release-draft-handoff.json",
        "create_issues_script": "create-issues.sh",
        "issue_bodies": issue_body_names,
    }


def _publication_handoff(plan: IterationPlan) -> dict[str, Any]:
    return {
        "publication_ok": plan.publication_ok,
        "candidate_issue_gate": plan.candidate_issue_gate,
        "visibility": plan.publication_visibility,
        "next_actions": plan.next_actions,
        "publication_next_actions": plan.publication_next_actions,
        "ref_context": plan.publication_ref_context,
        "worktree_clean": plan.publication_worktree_clean,
        "worktree_status": plan.publication_worktree_status,
        "publish_commands": plan.publication_publish_commands,
        "publish_script_path": plan.publication_publish_script_path,
        "publish_script_path_sha256": plan.publication_publish_script_path_sha256,
        "publish_script_command": plan.publication_publish_script_command,
        "publish_script_command_sha256": plan.publication_publish_script_command_sha256,
    }


def _release_draft_handoff(plan: IterationPlan) -> dict[str, Any]:
    return {
        "release_draft_path": plan.release_draft_path,
        "release_draft_issues": plan.release_draft_issues,
        "target_version": plan.target_version,
    }


def _issue_body_inventory(promotions: list[CandidatePromotion]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for promotion in promotions:
        body_name = f"{promotion.case_id}.md"
        body_bytes = f"{promotion.issue_body}\n".encode()
        inventory.append(
            {
                "case_id": promotion.case_id,
                "issue_body_name": body_name,
                "byte_count": len(body_bytes),
                "sha256": hashlib.sha256(body_bytes).hexdigest(),
            }
        )
    return inventory


def _issue_body_summary(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    digest_source = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "body_count": len(inventory),
        "total_byte_count": sum(int(item["byte_count"]) for item in inventory),
        "inventory_sha256": hashlib.sha256(digest_source).hexdigest(),
    }


def _issue_metadata_summary(metadata: list[dict[str, Any]]) -> dict[str, Any]:
    stable_metadata = [
        {
            "case_id": item["case_id"],
            "issue_title": item["issue_title"],
            "issue_labels": item["issue_labels"],
            "target_url": item["target_url"],
            "commands": item["commands"],
            "offline_commands": item["offline_commands"],
            "issue_body_name": item["issue_body_name"],
        }
        for item in metadata
    ]
    digest_source = json.dumps(stable_metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "metadata_count": len(stable_metadata),
        "metadata_sha256": hashlib.sha256(digest_source).hexdigest(),
    }


def _issue_metadata_for_summary(promotions: list[CandidatePromotion]) -> list[dict[str, Any]]:
    return [
        {
            "case_id": promotion.case_id,
            "issue_title": promotion.issue_title,
            "issue_labels": [*promotion.issue_labels],
            "target_url": promotion.target_url,
            "commands": promotion.commands,
            "offline_commands": promotion.offline_commands,
            "issue_body_name": f"{promotion.case_id}.md",
        }
        for promotion in promotions
    ]


def _issue_artifact_body_inventory_markdown(promotions: list[CandidatePromotion]) -> str:
    inventory = _issue_body_inventory(promotions)
    if not inventory:
        return "## Issue Body Inventory\n\n- No issue body inventory is available."
    lines = [
        "## Issue Body Inventory",
        "",
        "| Case | Issue Body | Bytes | SHA-256 |",
        "|------|------------|-------|---------|",
    ]
    for item in inventory:
        lines.append(
            f"| `{item['case_id']}` | `{item['issue_body_name']}` | "
            f"{item['byte_count']} | `{item['sha256']}` |"
        )
    return "\n".join(lines)


def _issue_artifact_body_summary_markdown(promotions: list[CandidatePromotion]) -> str:
    summary = _issue_body_summary(_issue_body_inventory(promotions))
    return "\n".join(
        [
            "## Issue Body Summary",
            "",
            f"- body_count: `{summary['body_count']}`",
            f"- total_byte_count: `{summary['total_byte_count']}`",
            f"- inventory_sha256: `{summary['inventory_sha256']}`",
        ]
    )


def _issue_artifact_bundle_summary(
    *,
    plan: IterationPlan,
    candidate_cases: list[str],
    review_order: list[str],
    issue_body_summary: dict[str, Any],
    issue_metadata_summary: dict[str, Any],
    create_issues_safety: dict[str, Any],
    artifact_files: dict[str, Any],
) -> dict[str, Any]:
    review_order_digest_source = json.dumps(
        review_order,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    create_issues_safety_contract = _issue_artifact_create_issues_safety_contract(create_issues_safety)
    publication_handoff = _publication_handoff(plan)
    release_draft_handoff = _release_draft_handoff(plan)
    candidate_issue_gate_evidence = plan.candidate_issue_gate.get("evidence")
    if not isinstance(candidate_issue_gate_evidence, dict):
        candidate_issue_gate_evidence = {}
    candidate_issue_gate_reason_descriptions = plan.candidate_issue_gate.get("reason_descriptions")
    if not isinstance(candidate_issue_gate_reason_descriptions, dict):
        candidate_issue_gate_reason_descriptions = {}
    candidate_issue_gate_reason_codes = plan.candidate_issue_gate.get("reason_codes")
    if not isinstance(candidate_issue_gate_reason_codes, list):
        candidate_issue_gate_reason_codes = []
    candidate_issue_gate_required_actions = plan.candidate_issue_gate.get("required_actions")
    if not isinstance(candidate_issue_gate_required_actions, list):
        candidate_issue_gate_required_actions = []
    candidate_issue_gate_primary_reason_code = (
        candidate_issue_gate_reason_codes[0] if candidate_issue_gate_reason_codes else None
    )
    candidate_issue_gate_primary_reason_description = None
    if candidate_issue_gate_primary_reason_code is not None:
        candidate_issue_gate_primary_reason_description = candidate_issue_gate_reason_descriptions.get(
            candidate_issue_gate_primary_reason_code
        )
    candidate_issue_gate_summary = plan.candidate_issue_gate.get("summary")
    return {
        "target_version": plan.target_version,
        "candidate_count": len(candidate_cases),
        "candidate_cases_sha256": _stable_json_sha256(candidate_cases),
        "body_count": issue_body_summary["body_count"],
        "issue_body_summary_sha256": _stable_json_sha256(issue_body_summary),
        "review_item_count": len(review_order),
        "review_order_sha256": hashlib.sha256(review_order_digest_source).hexdigest(),
        "inventory_sha256": issue_body_summary["inventory_sha256"],
        "issue_metadata_count": issue_metadata_summary["metadata_count"],
        "issue_metadata_sha256": issue_metadata_summary["metadata_sha256"],
        "artifact_files_key_count": len(artifact_files),
        "artifact_files_sha256": _stable_json_sha256(artifact_files),
        "issue_artifacts_command_sha256": _stable_json_sha256(plan.issue_artifacts_command),
        "publication_visibility_key_count": len(plan.publication_visibility),
        "publication_visibility_sha256": _stable_json_sha256(plan.publication_visibility),
        "publication_visibility_summary_sha256": _stable_json_sha256(
            plan.publication_visibility.get("summary")
        ),
        "blocker_count": len(plan.blockers),
        "blockers_sha256": _stable_json_sha256(plan.blockers),
        "next_action_count": len(plan.next_actions),
        "next_actions_sha256": _stable_json_sha256(plan.next_actions),
        "publication_next_action_count": len(plan.publication_next_actions),
        "publication_next_actions_sha256": _stable_json_sha256(plan.publication_next_actions),
        "publication_handoff_key_count": len(publication_handoff),
        "publication_handoff_sha256": _stable_json_sha256(publication_handoff),
        "publication_ref_context_key_count": len(plan.publication_ref_context),
        "publication_ref_context_sha256": _stable_json_sha256(plan.publication_ref_context),
        "publication_publish_command_count": plan.publication_publish_command_count,
        "publication_publish_commands_sha256": _stable_json_sha256(plan.publication_publish_commands),
        "publication_publish_script_path_sha256": _stable_json_sha256(
            plan.publication_publish_script_path
        ),
        "publication_publish_script_command_sha256": _stable_json_sha256(
            plan.publication_publish_script_command
        ),
        "publication_worktree_status_count": len(plan.publication_worktree_status),
        "publication_worktree_status_sha256": _stable_json_sha256(plan.publication_worktree_status),
        "release_draft_handoff_key_count": len(release_draft_handoff),
        "release_draft_handoff_sha256": _stable_json_sha256(release_draft_handoff),
        "release_draft_path": plan.release_draft_path,
        "release_draft_path_sha256": _stable_json_sha256(plan.release_draft_path),
        "release_draft_issues_sha256": _stable_json_sha256(plan.release_draft_issues),
        "validation_command_count": len(_issue_artifact_validation_commands(plan)),
        "validation_commands_sha256": _stable_json_sha256(_issue_artifact_validation_commands(plan)),
        "review_checklist_count": len(_issue_artifact_review_checklist()),
        "review_checklist_sha256": _stable_json_sha256(_issue_artifact_review_checklist()),
        "create_issues_safety_contract_key_count": len(create_issues_safety_contract),
        "create_issues_safety_contract_sha256": _stable_json_sha256(create_issues_safety_contract),
        "publication_ok": plan.publication_ok,
        "publication_visibility_status": plan.publication_visibility.get("status"),
        "publication_branch": plan.publication_ref_context.get("branch"),
        "publication_upstream": plan.publication_ref_context.get("upstream"),
        "publication_remote": plan.publication_ref_context.get("remote"),
        "publication_latest_tag": plan.publication_ref_context.get("latest_tag"),
        "publication_tag_commit": plan.publication_ref_context.get("tag_commit"),
        "publication_local_head": plan.publication_ref_context.get("local_head"),
        "publication_upstream_head": plan.publication_ref_context.get("upstream_head"),
        "publication_tag_points_at_head": plan.publication_ref_context.get("tag_points_at_head"),
        "publication_tag_commit_in_upstream": plan.publication_ref_context.get("tag_commit_in_upstream"),
        "publication_branch_published": plan.publication_ref_context.get("branch_published"),
        "publication_tag_published": plan.publication_ref_context.get("tag_published"),
        "publication_remote_branch_head": plan.publication_ref_context.get("remote_branch_head"),
        "publication_remote_tag_commit": plan.publication_ref_context.get("remote_tag_commit"),
        "publication_remote_checked": bool(plan.publication_ref_context.get("remote_checked", False)),
        "publication_ahead_count": plan.publication_ref_context.get("ahead_count"),
        "publication_behind_count": plan.publication_ref_context.get("behind_count"),
        "release_draft_ok": not plan.release_draft_issues,
        "release_draft_issue_count": len(plan.release_draft_issues),
        "candidate_issue_gate_key_count": len(plan.candidate_issue_gate),
        "candidate_issue_gate_sha256": _stable_json_sha256(plan.candidate_issue_gate),
        "candidate_issue_gate_status": plan.candidate_issue_gate.get("status"),
        "can_create_issues": bool(plan.candidate_issue_gate.get("can_create_issues", False)),
        "requires_maintainer_review": bool(plan.candidate_issue_gate.get("requires_maintainer_review", False)),
        "candidate_issue_gate_summary_sha256": _stable_json_sha256(candidate_issue_gate_summary),
        "candidate_issue_gate_evidence_key_count": len(candidate_issue_gate_evidence),
        "candidate_issue_gate_evidence_sha256": _stable_json_sha256(candidate_issue_gate_evidence),
        "candidate_issue_gate_reason_description_count": len(candidate_issue_gate_reason_descriptions),
        "candidate_issue_gate_reason_descriptions_sha256": _stable_json_sha256(
            candidate_issue_gate_reason_descriptions
        ),
        "candidate_issue_gate_reason_code_count": plan.candidate_issue_gate.get("reason_code_count"),
        "candidate_issue_gate_reason_codes_sha256": plan.candidate_issue_gate.get("reason_codes_sha256"),
        "candidate_issue_gate_primary_reason_code": candidate_issue_gate_primary_reason_code,
        "candidate_issue_gate_primary_reason_description": candidate_issue_gate_primary_reason_description,
        "candidate_issue_gate_required_action_count": plan.candidate_issue_gate.get("required_action_count"),
        "candidate_issue_gate_required_actions_sha256": plan.candidate_issue_gate.get("required_actions_sha256"),
        "candidate_issue_gate_primary_required_action": (
            candidate_issue_gate_required_actions[0] if candidate_issue_gate_required_actions else None
        ),
        "dry_run_supported": bool(create_issues_safety["dry_run_supported"]),
        "preflight_required": bool(create_issues_safety["preflight_required"]),
    }


def _summary_inline_code(value: Any) -> str:
    text = str(value)
    if "`" in text:
        return f"`` {text} ``"
    return f"`{text}`"


def _issue_artifact_bundle_summary_markdown(plan: IterationPlan) -> str:
    candidate_cases = [promotion.case_id for promotion in plan.candidate_promotions]
    issue_body_names = [f"{promotion.case_id}.md" for promotion in plan.candidate_promotions]
    review_order = [
        "README.md",
        "publication-handoff.json",
        "release-draft-handoff.json",
        "issue-metadata.json",
        *issue_body_names,
        "create-issues.sh",
    ]
    summary = _issue_artifact_bundle_summary(
        plan=plan,
        candidate_cases=candidate_cases,
        review_order=review_order,
        issue_body_summary=_issue_body_summary(_issue_body_inventory(plan.candidate_promotions)),
        issue_metadata_summary=_issue_metadata_summary(_issue_metadata_for_summary(plan.candidate_promotions)),
        create_issues_safety=_issue_artifact_create_issues_safety(Path("create-issues.sh")),
        artifact_files=_issue_artifact_files(issue_body_names),
    )
    return "\n".join(
        [
            "## Artifact Bundle Summary",
            "",
            f"- target_version: `{summary['target_version']}`",
            f"- candidate_count: `{summary['candidate_count']}`",
            f"- candidate_cases_sha256: `{summary['candidate_cases_sha256']}`",
            f"- body_count: `{summary['body_count']}`",
            f"- issue_body_summary_sha256: `{summary['issue_body_summary_sha256']}`",
            f"- review_item_count: `{summary['review_item_count']}`",
            f"- review_order_sha256: `{summary['review_order_sha256']}`",
            f"- inventory_sha256: `{summary['inventory_sha256']}`",
            f"- issue_metadata_count: `{summary['issue_metadata_count']}`",
            f"- issue_metadata_sha256: `{summary['issue_metadata_sha256']}`",
            f"- artifact_files_key_count: `{summary['artifact_files_key_count']}`",
            f"- artifact_files_sha256: `{summary['artifact_files_sha256']}`",
            f"- issue_artifacts_command_sha256: `{summary['issue_artifacts_command_sha256']}`",
            f"- publication_visibility_key_count: `{summary['publication_visibility_key_count']}`",
            f"- publication_visibility_sha256: `{summary['publication_visibility_sha256']}`",
            "- publication_visibility_summary_sha256: "
            f"`{summary['publication_visibility_summary_sha256']}`",
            f"- blocker_count: `{summary['blocker_count']}`",
            f"- blockers_sha256: `{summary['blockers_sha256']}`",
            f"- next_action_count: `{summary['next_action_count']}`",
            f"- next_actions_sha256: `{summary['next_actions_sha256']}`",
            f"- publication_next_action_count: `{summary['publication_next_action_count']}`",
            f"- publication_next_actions_sha256: `{summary['publication_next_actions_sha256']}`",
            f"- publication_handoff_key_count: `{summary['publication_handoff_key_count']}`",
            f"- publication_handoff_sha256: `{summary['publication_handoff_sha256']}`",
            f"- publication_ref_context_key_count: `{summary['publication_ref_context_key_count']}`",
            f"- publication_ref_context_sha256: `{summary['publication_ref_context_sha256']}`",
            f"- publication_publish_command_count: `{summary['publication_publish_command_count']}`",
            f"- publication_publish_commands_sha256: `{summary['publication_publish_commands_sha256']}`",
            "- publication_publish_script_path_sha256: "
            f"`{summary['publication_publish_script_path_sha256']}`",
            "- publication_publish_script_command_sha256: "
            f"`{summary['publication_publish_script_command_sha256']}`",
            f"- publication_worktree_status_count: `{summary['publication_worktree_status_count']}`",
            f"- publication_worktree_status_sha256: `{summary['publication_worktree_status_sha256']}`",
            f"- release_draft_handoff_key_count: `{summary['release_draft_handoff_key_count']}`",
            f"- release_draft_handoff_sha256: `{summary['release_draft_handoff_sha256']}`",
            f"- release_draft_path: `{summary['release_draft_path']}`",
            f"- release_draft_path_sha256: `{summary['release_draft_path_sha256']}`",
            f"- release_draft_issues_sha256: `{summary['release_draft_issues_sha256']}`",
            f"- validation_command_count: `{summary['validation_command_count']}`",
            f"- validation_commands_sha256: `{summary['validation_commands_sha256']}`",
            f"- review_checklist_count: `{summary['review_checklist_count']}`",
            f"- review_checklist_sha256: `{summary['review_checklist_sha256']}`",
            f"- create_issues_safety_contract_key_count: `{summary['create_issues_safety_contract_key_count']}`",
            f"- create_issues_safety_contract_sha256: `{summary['create_issues_safety_contract_sha256']}`",
            f"- publication_ok: `{str(summary['publication_ok']).lower()}`",
            f"- publication_visibility_status: `{summary['publication_visibility_status']}`",
            f"- publication_branch: `{summary['publication_branch']}`",
            f"- publication_upstream: `{summary['publication_upstream']}`",
            f"- publication_remote: `{summary['publication_remote']}`",
            f"- publication_latest_tag: `{summary['publication_latest_tag']}`",
            f"- publication_tag_commit: `{summary['publication_tag_commit']}`",
            f"- publication_local_head: `{summary['publication_local_head']}`",
            f"- publication_upstream_head: `{summary['publication_upstream_head']}`",
            "- publication_tag_points_at_head: "
            f"`{str(summary['publication_tag_points_at_head']).lower()}`",
            "- publication_tag_commit_in_upstream: "
            f"`{str(summary['publication_tag_commit_in_upstream']).lower()}`",
            f"- publication_branch_published: `{str(summary['publication_branch_published']).lower()}`",
            f"- publication_tag_published: `{str(summary['publication_tag_published']).lower()}`",
            f"- publication_remote_branch_head: `{summary['publication_remote_branch_head']}`",
            f"- publication_remote_tag_commit: `{summary['publication_remote_tag_commit']}`",
            f"- publication_remote_checked: `{str(summary['publication_remote_checked']).lower()}`",
            f"- publication_ahead_count: `{summary['publication_ahead_count']}`",
            f"- publication_behind_count: `{summary['publication_behind_count']}`",
            f"- release_draft_ok: `{str(summary['release_draft_ok']).lower()}`",
            f"- release_draft_issue_count: `{summary['release_draft_issue_count']}`",
            f"- candidate_issue_gate_key_count: `{summary['candidate_issue_gate_key_count']}`",
            f"- candidate_issue_gate_sha256: `{summary['candidate_issue_gate_sha256']}`",
            f"- candidate_issue_gate_status: `{summary['candidate_issue_gate_status']}`",
            f"- can_create_issues: `{str(summary['can_create_issues']).lower()}`",
            f"- requires_maintainer_review: `{str(summary['requires_maintainer_review']).lower()}`",
            f"- candidate_issue_gate_summary_sha256: `{summary['candidate_issue_gate_summary_sha256']}`",
            f"- candidate_issue_gate_evidence_key_count: `{summary['candidate_issue_gate_evidence_key_count']}`",
            f"- candidate_issue_gate_evidence_sha256: `{summary['candidate_issue_gate_evidence_sha256']}`",
            "- candidate_issue_gate_reason_description_count: "
            f"`{summary['candidate_issue_gate_reason_description_count']}`",
            "- candidate_issue_gate_reason_descriptions_sha256: "
            f"`{summary['candidate_issue_gate_reason_descriptions_sha256']}`",
            f"- candidate_issue_gate_reason_code_count: `{summary['candidate_issue_gate_reason_code_count']}`",
            f"- candidate_issue_gate_reason_codes_sha256: `{summary['candidate_issue_gate_reason_codes_sha256']}`",
            "- candidate_issue_gate_primary_reason_code: "
            f"{_summary_inline_code(summary['candidate_issue_gate_primary_reason_code'])}",
            "- candidate_issue_gate_primary_reason_description: "
            f"{_summary_inline_code(summary['candidate_issue_gate_primary_reason_description'])}",
            f"- candidate_issue_gate_required_action_count: `{summary['candidate_issue_gate_required_action_count']}`",
            "- candidate_issue_gate_required_actions_sha256: "
            f"`{summary['candidate_issue_gate_required_actions_sha256']}`",
            "- candidate_issue_gate_primary_required_action: "
            f"{_summary_inline_code(summary['candidate_issue_gate_primary_required_action'])}",
            f"- dry_run_supported: `{str(summary['dry_run_supported']).lower()}`",
            f"- preflight_required: `{str(summary['preflight_required']).lower()}`",
        ]
    )


def _issue_artifact_candidate_summary(promotions: list[CandidatePromotion]) -> str:
    if not promotions:
        return "## Candidate Summary\n\n- No candidate issue metadata is available."
    lines = [
        "## Candidate Summary",
        "",
        "| Case | Issue Body | Target URL | Candidate Commands | Offline Validation Commands |",
        "|------|------------|------------|--------------------|-----------------------------|",
    ]
    for promotion in promotions:
        lines.append(
            f"| `{promotion.case_id}` | `{promotion.case_id}.md` | {promotion.target_url or 'Not declared.'} | "
            f"{len(promotion.commands)} | {len(promotion.offline_commands)} |"
        )
    return "\n".join(lines)


def _gh_issue_create_command(promotion: CandidatePromotion, body_path: Path) -> str:
    parts = [
        "gh",
        "issue",
        "create",
        "--title",
        promotion.issue_title,
        "--body-file",
        str(body_path),
    ]
    for label in promotion.issue_labels:
        parts.extend(["--label", label])
    return " ".join(shlex.quote(part) for part in parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan the next verified cliany-site release slice.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--target-version", help="Target release version. Defaults to next patch version.")
    parser.add_argument("--min-days", type=int, default=3, help="Minimum unique commit days expected this week.")
    parser.add_argument("--min-case-assets", type=int, default=8, help="Minimum tracked case assets expected.")
    parser.add_argument("--today", help="Override current date as YYYY-MM-DD, for audits.")
    parser.add_argument("--report", type=Path, help="Optional Markdown plan report path.")
    parser.add_argument(
        "--issues-dir",
        type=Path,
        help="Optional directory for candidate issue body files, metadata JSON, and a reviewable gh script.",
    )
    args = parser.parse_args(argv)

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None
    plan = build_plan(
        ROOT,
        today=today,
        target_version=args.target_version,
        min_commit_days=args.min_days,
        min_case_assets=args.min_case_assets,
    )
    if args.report:
        _write_markdown_report(plan, args.report)
    if args.issues_dir:
        _write_candidate_issue_files(plan, args.issues_dir)
    if args.json:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(plan)
    return 0


if __name__ == "__main__":
    sys.exit(main())
