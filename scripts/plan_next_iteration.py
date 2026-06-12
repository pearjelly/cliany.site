#!/usr/bin/env python3
"""Plan the next small cliany-site release slice from local project evidence."""

from __future__ import annotations

import argparse
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
    publication_next_actions: list[str]
    publication_publish_commands: list[str]
    publication_ref_context: dict[str, Any]
    publication_worktree_clean: bool
    publication_worktree_status: list[str]
    publication_publish_script_command: str
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
            "publication_next_actions": self.publication_next_actions,
            "publication_publish_commands": self.publication_publish_commands,
            "publication_ref_context": self.publication_ref_context,
            "publication_worktree_clean": self.publication_worktree_clean,
            "publication_worktree_status": self.publication_worktree_status,
            "publication_publish_script_command": self.publication_publish_script_command,
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
    if not bool(getattr(publication, "ok", False)):
        actions = _publication_next_actions(publication) or [
            "Run python scripts/check_release_publication.py --json and resolve publication blockers."
        ]
        return {
            "status": "blocked_by_publication",
            "can_create_issues": False,
            "requires_maintainer_review": True,
            "summary": "Do not create candidate issues until the latest local release is publicly visible.",
            "required_actions": actions,
            "evidence": evidence,
        }
    if release_draft_issues:
        return {
            "status": "review_required",
            "can_create_issues": True,
            "requires_maintainer_review": True,
            "summary": "Release draft issues must be resolved or intentionally deferred before tagging.",
            "required_actions": release_draft_issues,
            "evidence": evidence,
        }
    return {
        "status": "ready",
        "can_create_issues": True,
        "requires_maintainer_review": False,
        "summary": "Candidate issues can be created after reviewing the generated artifacts.",
        "required_actions": [],
        "evidence": evidence,
    }


def _candidate_issue_gate_evidence(readiness: Any, publication: Any) -> dict[str, Any]:
    draft = getattr(readiness, "draft", None)
    release_draft_issues = _release_draft_issues(readiness)
    publication_visibility = _publication_visibility(publication)
    return {
        "publication_ok": bool(getattr(publication, "ok", False)),
        "publication_visibility_status": publication_visibility.get("status") or "(unknown)",
        "publication_remote_checked": bool(getattr(publication, "remote_checked", False)),
        "publication_branch": str(getattr(publication, "branch", "") or "HEAD"),
        "publication_latest_tag": str(getattr(publication, "latest_tag", "") or "(none)"),
        "publication_ahead_count": getattr(publication, "ahead_count", None),
        "release_draft_path": str(getattr(draft, "path", "") or ""),
        "release_draft_issue_count": len(release_draft_issues),
    }


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
        "--publish-script /tmp/cliany-publish-release.sh"
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
        publication_next_actions=_publication_next_actions(publication),
        publication_publish_commands=_publication_publish_commands(publication),
        publication_ref_context=_publication_ref_context(publication),
        publication_worktree_clean=_publication_worktree_clean(publication),
        publication_worktree_status=_publication_worktree_status(publication),
        publication_publish_script_command=publication_publish_script_command,
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
    if plan.publication_next_actions:
        print("publication_next_actions:")
        for action in plan.publication_next_actions:
            print(f"- {action}")
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
    print(f"publication_publish_script_command: {plan.publication_publish_script_command}")
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
    publication_script = _publication_script_markdown(plan.publication_publish_script_command)
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
    actions = gate.get("required_actions")
    evidence = gate.get("evidence")
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
        ("publication_remote_checked", evidence.get("publication_remote_checked")),
        ("publication_branch", evidence.get("publication_branch")),
        ("publication_latest_tag", evidence.get("publication_latest_tag")),
        ("publication_ahead_count", evidence.get("publication_ahead_count")),
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


def _publication_script_markdown(command: str) -> str:
    return f"""## Publication Publish Script

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
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Review these commands before running; they create GitHub issues in the current repository.",
        "# Stop early if the latest local release is not publicly visible yet.",
        'REPO_ROOT="$(git rev-parse --show-toplevel)"',
        'cd "$REPO_ROOT"',
        'PREFLIGHT_JSON="/tmp/cliany-issue-publication-check.json"',
        'if ! python scripts/check_release_publication.py --strict --json >"$PREFLIGHT_JSON"; then',
        '  echo "Release publication preflight failed; review $PREFLIGHT_JSON before creating candidate issues." >&2',
        '  cat "$PREFLIGHT_JSON" >&2',
        "  exit 1",
        "fi",
    ]
    for promotion in plan.candidate_promotions:
        body_path = directory / f"{promotion.case_id}.md"
        body_path.write_text(promotion.issue_body + "\n", encoding="utf-8")
        labels = [*promotion.issue_labels]
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
                "create_command": _gh_issue_create_command(promotion, body_path),
            }
        )
        script_lines.extend(["", _gh_issue_create_command(promotion, body_path)])

    issue_body_names = [f"{promotion.case_id}.md" for promotion in plan.candidate_promotions]
    candidate_cases = [promotion.case_id for promotion in plan.candidate_promotions]
    artifact_manifest = {
        "schema_version": 1,
        "target_version": plan.target_version,
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
        "publication_publish_script_command": plan.publication_publish_script_command,
        "release_draft_path": plan.release_draft_path,
        "release_draft_issues": plan.release_draft_issues,
        "issue_artifacts_command": plan.issue_artifacts_command,
        "files": {
            "readme": "README.md",
            "issue_metadata": "issue-metadata.json",
            "publication_handoff": "publication-handoff.json",
            "release_draft_handoff": "release-draft-handoff.json",
            "create_issues_script": "create-issues.sh",
            "issue_bodies": issue_body_names,
        },
        "review_order": [
            "README.md",
            "publication-handoff.json",
            "release-draft-handoff.json",
            "issue-metadata.json",
            *issue_body_names,
            "create-issues.sh",
        ],
        "review_checklist": _issue_artifact_review_checklist(),
        "validation_commands": [
            plan.issue_artifacts_command,
            f"python scripts/plan_next_iteration.py --target-version {plan.target_version} --json",
            f"python scripts/release_readiness.py --target-version {plan.target_version} --json",
            "python scripts/check_release_publication.py --json",
            "python scripts/validate_cases.py --strict",
        ],
    }
    (directory / "artifact-manifest.json").write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (directory / "issue-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    publication_handoff = {
        "publication_ok": plan.publication_ok,
        "candidate_issue_gate": plan.candidate_issue_gate,
        "visibility": plan.publication_visibility,
        "next_actions": plan.next_actions,
        "publication_next_actions": plan.publication_next_actions,
        "ref_context": plan.publication_ref_context,
        "worktree_clean": plan.publication_worktree_clean,
        "worktree_status": plan.publication_worktree_status,
        "publish_commands": plan.publication_publish_commands,
        "publish_script_command": plan.publication_publish_script_command,
    }
    (directory / "publication-handoff.json").write_text(
        json.dumps(publication_handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    release_draft_handoff = {
        "release_draft_path": plan.release_draft_path,
        "release_draft_issues": plan.release_draft_issues,
        "target_version": plan.target_version,
    }
    (directory / "release-draft-handoff.json").write_text(
        json.dumps(release_draft_handoff, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    script_path = directory / "create-issues.sh"
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    script_path.chmod(0o755)
    (directory / "README.md").write_text(_render_issue_artifacts_readme(plan), encoding="utf-8")


def _render_issue_artifacts_readme(plan: IterationPlan) -> str:
    body_files = "\n".join(f"- `{promotion.case_id}.md`" for promotion in plan.candidate_promotions)
    body_files = body_files or "- No candidate issue body files were generated."
    candidate_summary = _issue_artifact_candidate_summary(plan.candidate_promotions)
    gate_latest_tag = _format_context_value(_candidate_issue_gate_evidence_value(plan, "publication_latest_tag"))
    gate_ahead_count = _format_context_value(_candidate_issue_gate_evidence_value(plan, "publication_ahead_count"))
    gate_draft_issues = _format_context_value(_candidate_issue_gate_evidence_value(plan, "release_draft_issue_count"))
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
  one `gh issue create` command per candidate.
{body_files}

{candidate_summary}

## Publication Handoff

- publication_ok: `{str(plan.publication_ok).lower()}`
- candidate_issue_gate: `{_format_context_value(plan.candidate_issue_gate.get("status"))}`
- can_create_issues: `{str(bool(plan.candidate_issue_gate.get("can_create_issues", False))).lower()}`
- gate_summary: {_format_context_value(plan.candidate_issue_gate.get("summary"))}
- gate_evidence_latest_tag: `{gate_latest_tag}`
- gate_evidence_ahead_count: `{gate_ahead_count}`
- gate_evidence_release_draft_issues: `{gate_draft_issues}`
- visibility: `{_format_context_value(plan.publication_visibility.get("status"))}`
- visibility_summary: {_format_context_value(plan.publication_visibility.get("summary"))}
- latest_tag: `{_format_context_value(plan.publication_ref_context.get("latest_tag"))}`
- local_head: `{_format_context_value(plan.publication_ref_context.get("local_head"))}`
- worktree_clean: `{str(plan.publication_worktree_clean).lower()}`
- Review `publication-handoff.json` before running `create-issues.sh`.

### Publication Next Actions

{_issue_artifact_publication_next_actions(plan)}

### Publication Publish Script

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
{plan.issue_artifacts_command}
python scripts/plan_next_iteration.py --target-version {plan.target_version} --json
python scripts/validate_cases.py --strict
```

## Create Issues

`create-issues.sh` is generated for review. It is not executed by `plan_next_iteration.py`.
Run it only after checking `issue-metadata.json` and the body files. The script runs
`python scripts/check_release_publication.py --strict --json` before creating issues and
writes the preflight JSON to `/tmp/cliany-issue-publication-check.json`. If the preflight
fails, it prints that JSON before exiting.
"""


def _candidate_issue_gate_evidence_value(plan: IterationPlan, key: str) -> object:
    evidence = plan.candidate_issue_gate.get("evidence")
    if not isinstance(evidence, dict):
        return None
    return evidence.get(key)


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
