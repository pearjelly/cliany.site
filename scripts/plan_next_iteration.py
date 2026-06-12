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
    adapter_package: str
    metadata_validation: str
    online_smoke: str
    issue_body: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "issue_title": self.issue_title,
            "issue_labels": self.issue_labels,
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
    release_draft_path: str

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
            "release_draft_path": self.release_draft_path,
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
                adapter_package=_promotion_value(promotion, "adapter_package"),
                metadata_validation=_promotion_value(promotion, "metadata_validation"),
                online_smoke=_promotion_value(promotion, "online_smoke"),
                issue_body=_candidate_issue_body(
                    case_id=str(case.id),
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
    adapter_package: str,
    metadata_validation: str,
    online_smoke: str,
) -> str:
    return "\n".join(
        [
            f"## Scope: promote candidate case `{case_id}`",
            "",
            "Move this candidate case one step closer to `active` without changing its status early.",
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
        release_draft_path=f"docs/releases/v{readiness.target_version}-draft.md",
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


def _render_markdown(plan: IterationPlan) -> str:
    candidate_cases = ", ".join(f"`{case_id}`" for case_id in plan.candidate_cases) or "-"
    blockers = "\n".join(f"- {blocker}" for blocker in plan.blockers) or "- None."
    next_actions = "\n".join(f"- {action}" for action in plan.next_actions)
    validation = "\n".join(f"- `{command}`" for command in plan.validation_commands)
    promotion_lines = _candidate_promotion_markdown(plan.candidate_promotions)
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

## Release Draft

- `{plan.release_draft_path}`
"""


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
                "issue_body_file": str(body_path),
                "create_command": _gh_issue_create_command(promotion, body_path),
            }
        )
        script_lines.extend(["", _gh_issue_create_command(promotion, body_path)])

    (directory / "issue-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    script_path = directory / "create-issues.sh"
    script_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    script_path.chmod(0o755)


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
