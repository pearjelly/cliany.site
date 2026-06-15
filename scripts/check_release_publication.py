#!/usr/bin/env python3
"""Check whether the latest local release is visible from the configured upstream."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PublicationReport:
    ok: bool
    repo_root: str
    worktree_clean: bool
    worktree_status: list[str]
    branch: str | None
    upstream: str | None
    remote: str
    local_head: str | None
    upstream_head: str | None
    ahead_count: int | None
    behind_count: int | None
    latest_tag: str | None
    tag_commit: str | None
    tag_points_at_head: bool
    tag_commit_in_upstream: bool | None
    remote_checked: bool
    remote_branch_head: str | None
    remote_tag_commit: str | None
    branch_published: bool | None
    tag_published: bool | None

    def to_dict(self) -> dict[str, Any]:
        next_actions = _next_action_lines(self)
        publish_commands = _publish_command_lines(self)
        tag_publish_decision = _tag_publish_decision(self)
        return {
            "ok": self.ok,
            "repo_root": self.repo_root,
            "worktree_clean": self.worktree_clean,
            "worktree_status": self.worktree_status,
            "branch": self.branch,
            "upstream": self.upstream,
            "remote": self.remote,
            "local_head": self.local_head,
            "upstream_head": self.upstream_head,
            "ahead_count": self.ahead_count,
            "behind_count": self.behind_count,
            "latest_tag": self.latest_tag,
            "tag_commit": self.tag_commit,
            "tag_points_at_head": self.tag_points_at_head,
            "tag_commit_in_upstream": self.tag_commit_in_upstream,
            "remote_checked": self.remote_checked,
            "remote_branch_head": self.remote_branch_head,
            "remote_tag_commit": self.remote_tag_commit,
            "branch_published": self.branch_published,
            "tag_published": self.tag_published,
            "tag_publish_decision": tag_publish_decision,
            "next_action_count": len(next_actions),
            "next_actions": next_actions,
            "publish_command_count": len(publish_commands),
            "publish_commands": publish_commands,
        }


def _run_git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def _optional_git(args: list[str], cwd: Path) -> str | None:
    try:
        return _run_git(args, cwd)
    except subprocess.CalledProcessError:
        return None


def _optional_int_git(args: list[str], cwd: Path) -> int | None:
    output = _optional_git(args, cwd)
    return int(output) if output is not None and output else None


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _branch_name(root: Path) -> str | None:
    branch = _optional_git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if not branch or branch == "HEAD":
        return None
    return branch


def _upstream_name(root: Path) -> str | None:
    return _optional_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root)


def _remote_from_upstream(upstream: str | None, fallback: str) -> str:
    if upstream and "/" in upstream:
        return upstream.split("/", 1)[0]
    return fallback


def _ls_remote_ref(root: Path, remote: str, ref: str) -> str | None:
    output = _optional_git(["ls-remote", remote, ref], root)
    if not output:
        return None
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0]
    return None


def _worktree_status(root: Path) -> list[str]:
    status = _optional_git(["status", "--porcelain"], root)
    return status.splitlines() if status else []


def build_report(root: Path = ROOT, *, remote_check: bool = False, remote: str = "origin") -> PublicationReport:
    branch = _branch_name(root)
    upstream = _upstream_name(root)
    remote_name = _remote_from_upstream(upstream, remote)
    worktree_status = _worktree_status(root)
    worktree_clean = not worktree_status
    local_head = _optional_git(["rev-parse", "HEAD"], root)
    upstream_head = _optional_git(["rev-parse", upstream], root) if upstream else None
    ahead_count = _optional_int_git(["rev-list", "--count", f"{upstream}..HEAD"], root) if upstream else None
    behind_count = _optional_int_git(["rev-list", "--count", f"HEAD..{upstream}"], root) if upstream else None
    latest_tag = _optional_git(["describe", "--tags", "--abbrev=0"], root)
    tag_commit = _optional_git(["rev-list", "-n", "1", latest_tag], root) if latest_tag else None
    tag_points_at_head = bool(local_head and tag_commit and local_head == tag_commit)
    tag_commit_in_upstream = (
        _is_ancestor(root, tag_commit, upstream) if tag_commit and upstream else None
    )

    remote_branch_head = None
    remote_tag_commit = None
    branch_published = ahead_count == 0 if ahead_count is not None else None
    tag_published = tag_commit_in_upstream

    if remote_check:
        remote_branch_head = _ls_remote_ref(root, remote_name, f"refs/heads/{branch}") if branch else None
        remote_tag_commit = _ls_remote_ref(root, remote_name, f"refs/tags/{latest_tag}") if latest_tag else None
        branch_published = bool(local_head and remote_branch_head == local_head)
        tag_published = bool(tag_commit and remote_tag_commit == tag_commit)

    ok = bool(
        branch_published is True
        and tag_published is True
        and tag_points_at_head
        and worktree_clean
        and latest_tag
    )

    return PublicationReport(
        ok=ok,
        repo_root=str(root.resolve()),
        worktree_clean=worktree_clean,
        worktree_status=worktree_status,
        branch=branch,
        upstream=upstream,
        remote=remote_name,
        local_head=local_head,
        upstream_head=upstream_head,
        ahead_count=ahead_count,
        behind_count=behind_count,
        latest_tag=latest_tag,
        tag_commit=tag_commit,
        tag_points_at_head=tag_points_at_head,
        tag_commit_in_upstream=tag_commit_in_upstream,
        remote_checked=remote_check,
        remote_branch_head=remote_branch_head,
        remote_tag_commit=remote_tag_commit,
        branch_published=branch_published,
        tag_published=tag_published,
    )


def _next_action_lines(report: PublicationReport) -> list[str]:
    actions: list[str] = []
    branch = report.branch or "HEAD"
    if not report.worktree_clean:
        actions.append("Commit, stash, or discard local worktree changes before publishing release refs.")
    if not report.upstream:
        actions.append(f"Set an upstream branch for `{branch}` before checking publication status.")
    if report.ahead_count and report.ahead_count > 0:
        actions.append(
            f"Push `{branch}` to `{report.remote}`; local branch is ahead by "
            f"`{report.ahead_count}` commits."
        )
    if report.behind_count and report.behind_count > 0:
        actions.append(
            f"Reconcile `{branch}` with `{report.upstream}`; local branch is behind by "
            f"`{report.behind_count}` commits."
        )
    if not report.latest_tag:
        actions.append("Create a release tag before checking publication status.")
    elif not report.tag_points_at_head:
        actions.append(
            f"Move to the `{report.latest_tag}` commit or create a new release tag at HEAD before publishing."
        )
    if report.latest_tag and report.tag_published is False:
        if report.remote_checked:
            actions.append(f"Push tag `{report.latest_tag}` to `{report.remote}`; remote tag is missing or stale.")
        else:
            actions.append(
                f"Push tag `{report.latest_tag}` after the branch is published, or rerun with `--remote` "
                "to verify the live remote tag."
            )
    if not report.remote_checked:
        actions.append("Rerun with `--remote` when network access is available to verify live remote refs.")
    return actions


def _publish_command_lines(report: PublicationReport) -> list[str]:
    if not report.worktree_clean:
        return ["python scripts/check_release_publication.py --json"]

    commands: list[str] = []
    branch = report.branch
    remote = shlex.quote(report.remote)
    if branch and not report.upstream:
        commands.append(f"git push -u {remote} {shlex.quote(branch)}")
    elif branch and (
        (report.ahead_count is not None and report.ahead_count > 0)
        or report.branch_published is False
    ):
        commands.append(f"git push {remote} {shlex.quote(branch)}")

    if report.latest_tag and report.tag_points_at_head and report.tag_published is False:
        commands.append(f"git push {remote} {shlex.quote(report.latest_tag)}")

    if commands or not report.remote_checked:
        commands.append("python scripts/check_release_publication.py --remote --json")
    return commands


def _tag_publish_decision(report: PublicationReport) -> dict[str, Any]:
    if not report.latest_tag:
        return {
            "status": "missing_tag",
            "can_push_tag": False,
            "latest_tag": None,
            "tag_points_at_head": report.tag_points_at_head,
            "tag_published": report.tag_published,
            "required_action": "Create a release tag before publishing a tag.",
        }
    if not report.tag_points_at_head:
        return {
            "status": "manual_decision_required",
            "can_push_tag": False,
            "latest_tag": report.latest_tag,
            "tag_points_at_head": False,
            "tag_published": report.tag_published,
            "required_action": (
                "Move to the latest tag commit or create a new release tag at HEAD "
                "before publishing a tag."
            ),
        }
    if report.tag_published is True:
        return {
            "status": "published",
            "can_push_tag": False,
            "latest_tag": report.latest_tag,
            "tag_points_at_head": True,
            "tag_published": True,
            "required_action": None,
        }
    if not report.worktree_clean:
        return {
            "status": "blocked_by_worktree",
            "can_push_tag": False,
            "latest_tag": report.latest_tag,
            "tag_points_at_head": True,
            "tag_published": report.tag_published,
            "required_action": "Commit, stash, or discard local worktree changes before publishing release refs.",
        }
    if report.tag_published is False:
        return {
            "status": "ready_to_push",
            "can_push_tag": True,
            "latest_tag": report.latest_tag,
            "tag_points_at_head": True,
            "tag_published": False,
            "required_action": f"Push tag `{report.latest_tag}` after the branch is published.",
        }
    return {
        "status": "needs_remote_check",
        "can_push_tag": False,
        "latest_tag": report.latest_tag,
        "tag_points_at_head": True,
        "tag_published": report.tag_published,
        "required_action": "Rerun with `--remote` to verify the live remote tag.",
    }


def _print_text(report: PublicationReport) -> None:
    next_actions = _next_action_lines(report)
    publish_commands = _publish_command_lines(report)
    tag_publish_decision = _tag_publish_decision(report)
    print("=== cliany-site release publication ===")
    print(f"ok: {report.ok}")
    print(f"repo_root: {report.repo_root}")
    print(f"worktree_clean: {report.worktree_clean}")
    print(f"branch: {report.branch or '(detached)'}")
    print(f"upstream: {report.upstream or '(none)'}")
    print(f"remote: {report.remote}")
    print(f"ahead_count: {report.ahead_count}")
    print(f"behind_count: {report.behind_count}")
    print(f"latest_tag: {report.latest_tag or '(none)'}")
    print(f"tag_points_at_head: {report.tag_points_at_head}")
    print(f"branch_published: {report.branch_published}")
    print(f"tag_published: {report.tag_published}")
    print(f"tag_publish_decision: {tag_publish_decision['status']}")
    print(f"remote_checked: {report.remote_checked}")
    print(f"next_action_count: {len(next_actions)}")
    print(f"publish_command_count: {len(publish_commands)}")
    if report.worktree_status:
        print("worktree_status:")
        for line in report.worktree_status:
            print(f"- {line}")
    if next_actions:
        print("next_actions:")
        for action in next_actions:
            print(f"- {action}")
    if publish_commands:
        print("publish_commands:")
        for command in publish_commands:
            print(f"- {command}")


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "true" if value else "false"


def _format_value(value: object) -> str:
    if value is None:
        return "(none)"
    return str(value)


def _write_markdown_report(report: PublicationReport, path: Path) -> None:
    next_actions = _next_action_lines(report)
    publish_commands = _publish_command_lines(report)
    tag_publish_decision = _tag_publish_decision(report)
    lines = [
        "# cliany-site Release Publication",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| ok | `{_format_bool(report.ok)}` |",
        f"| repo_root | `{report.repo_root}` |",
        f"| worktree_clean | `{_format_bool(report.worktree_clean)}` |",
        f"| branch | `{_format_value(report.branch)}` |",
        f"| upstream | `{_format_value(report.upstream)}` |",
        f"| remote | `{report.remote}` |",
        f"| ahead_count | `{_format_value(report.ahead_count)}` |",
        f"| behind_count | `{_format_value(report.behind_count)}` |",
        f"| latest_tag | `{_format_value(report.latest_tag)}` |",
        f"| tag_points_at_head | `{_format_bool(report.tag_points_at_head)}` |",
        f"| branch_published | `{_format_bool(report.branch_published)}` |",
        f"| tag_published | `{_format_bool(report.tag_published)}` |",
        f"| tag_publish_decision | `{tag_publish_decision['status']}` |",
        f"| tag_can_push | `{_format_bool(tag_publish_decision['can_push_tag'])}` |",
        f"| remote_checked | `{_format_bool(report.remote_checked)}` |",
        f"| next_action_count | `{len(next_actions)}` |",
        f"| publish_command_count | `{len(publish_commands)}` |",
        "",
        "## Refs",
        "",
        "| Ref | Commit |",
        "|-----|--------|",
        f"| local HEAD | `{_format_value(report.local_head)}` |",
        f"| upstream HEAD | `{_format_value(report.upstream_head)}` |",
        f"| latest tag commit | `{_format_value(report.tag_commit)}` |",
        f"| remote branch HEAD | `{_format_value(report.remote_branch_head)}` |",
        f"| remote tag commit | `{_format_value(report.remote_tag_commit)}` |",
    ]
    if next_actions:
        lines.extend(["", "## Next Actions", "", *(f"- {action}" for action in next_actions)])
    else:
        lines.extend(["", "## Next Actions", "", "- Release branch and tag are published."])
    lines.extend(
        [
            "",
            "## Tag Publish Decision",
            "",
            f"- status: `{tag_publish_decision['status']}`",
            f"- can_push_tag: `{_format_bool(tag_publish_decision['can_push_tag'])}`",
            f"- latest_tag: `{_format_value(tag_publish_decision['latest_tag'])}`",
            f"- required_action: `{_format_value(tag_publish_decision['required_action'])}`",
        ]
    )
    if report.worktree_status:
        lines.extend(["", "## Worktree Status", "", "```text", *report.worktree_status, "```"])
    else:
        lines.extend(["", "## Worktree Status", "", "- Worktree is clean."])
    if publish_commands:
        lines.extend(["", "## Publish Commands", "", "```bash", *publish_commands, "```"])
    else:
        lines.extend(["", "## Publish Commands", "", "- No publish commands are needed."])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_publish_script(report: PublicationReport, path: Path) -> None:
    commands = _publish_command_lines(report)
    repo_root = report.repo_root
    expected_local_head = report.local_head or ""
    expected_latest_tag = report.latest_tag or ""
    expected_tag_commit = report.tag_commit or ""
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Review these commands before running; they publish the current release branch/tag.",
        "# Generated by scripts/check_release_publication.py --publish-script.",
        "#",
        "# Publication context:",
        f"# - repo_root: {repo_root}",
        f"# - branch: {_format_value(report.branch)}",
        f"# - upstream: {_format_value(report.upstream)}",
        f"# - remote: {report.remote}",
        f"# - latest_tag: {_format_value(report.latest_tag)}",
        f"# - local_head: {_format_value(report.local_head)}",
        f"# - tag_commit: {_format_value(report.tag_commit)}",
        f"# - ahead_count: {_format_value(report.ahead_count)}",
        f"# - behind_count: {_format_value(report.behind_count)}",
        f"# - remote_checked: {_format_bool(report.remote_checked)}",
        *_publish_script_review_notes(report),
        "",
        f"REPO_ROOT={shlex.quote(repo_root)}",
        f"EXPECTED_LOCAL_HEAD={shlex.quote(expected_local_head)}",
        f"EXPECTED_LATEST_TAG={shlex.quote(expected_latest_tag)}",
        f"EXPECTED_TAG_COMMIT={shlex.quote(expected_tag_commit)}",
        "",
        'if [[ ! -d "$REPO_ROOT" ]]; then',
        '  echo "Publish script is stale: repo root $REPO_ROOT does not exist." >&2',
        "  exit 1",
        "fi",
        'cd "$REPO_ROOT"',
        'CURRENT_REPO_ROOT="$(git rev-parse --show-toplevel)"',
        'if [[ "$CURRENT_REPO_ROOT" != "$REPO_ROOT" ]]; then',
        '  echo "Publish script is stale: repo root is $CURRENT_REPO_ROOT, expected $REPO_ROOT." >&2',
        "  exit 1",
        "fi",
        "",
        'CURRENT_LOCAL_HEAD="$(git rev-parse HEAD)"',
        'if [[ -n "$EXPECTED_LOCAL_HEAD" && "$CURRENT_LOCAL_HEAD" != "$EXPECTED_LOCAL_HEAD" ]]; then',
        '  echo "Publish script is stale: HEAD is $CURRENT_LOCAL_HEAD, expected $EXPECTED_LOCAL_HEAD." >&2',
        "  exit 1",
        "fi",
        'if [[ -n "$EXPECTED_LATEST_TAG" ]]; then',
        '  if ! CURRENT_LATEST_TAG="$(git describe --tags --abbrev=0 2>/dev/null)"; then',
        '    echo "Publish script is stale: expected tag $EXPECTED_LATEST_TAG, but no local tag was found." >&2',
        "    exit 1",
        "  fi",
        '  if [[ "$CURRENT_LATEST_TAG" != "$EXPECTED_LATEST_TAG" ]]; then',
        '    echo "Publish script is stale: latest tag is $CURRENT_LATEST_TAG, expected $EXPECTED_LATEST_TAG." >&2',
        "    exit 1",
        "  fi",
        '  if ! CURRENT_TAG_COMMIT="$(git rev-list -n 1 "$EXPECTED_LATEST_TAG" 2>/dev/null)"; then',
        '    echo "Publish script is stale: expected tag $EXPECTED_LATEST_TAG is missing." >&2',
        "    exit 1",
        "  fi",
        '  if [[ -n "$EXPECTED_TAG_COMMIT" && "$CURRENT_TAG_COMMIT" != "$EXPECTED_TAG_COMMIT" ]]; then',
        '    echo "Publish script is stale: tag $EXPECTED_LATEST_TAG points at $CURRENT_TAG_COMMIT, '
        'expected $EXPECTED_TAG_COMMIT." >&2',
        "    exit 1",
        "  fi",
        "fi",
        'CURRENT_WORKTREE_STATUS="$(git status --porcelain)"',
        'if [[ -n "$CURRENT_WORKTREE_STATUS" ]]; then',
        '  echo "Publish script is stale: worktree has uncommitted changes." >&2',
        '  echo "$CURRENT_WORKTREE_STATUS" >&2',
        "  exit 1",
        "fi",
        "",
    ]
    if commands:
        script_lines.extend(commands)
    else:
        script_lines.append('echo "No publish commands are needed."')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def _publish_script_review_notes(report: PublicationReport) -> list[str]:
    if report.latest_tag and not report.tag_points_at_head:
        return [
            "#",
            "# Publication review notes:",
            f"# - Latest tag {report.latest_tag} does not point at HEAD.",
            "# - This script will not push that tag automatically.",
            "# - Publish the branch first, then choose whether to move to the tag commit",
            "#   or create a new release tag at HEAD before publishing a tag.",
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether the latest local release has been published.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when publication checks are not satisfied.",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Check live remote branch and tag refs with git ls-remote.",
    )
    parser.add_argument("--remote-name", default="origin", help="Fallback remote name when no upstream is configured.")
    parser.add_argument("--report", type=Path, help="Write a Markdown publication report to this path.")
    parser.add_argument("--publish-script", type=Path, help="Write a reviewable shell script with publish commands.")
    args = parser.parse_args(argv)

    report = build_report(ROOT, remote_check=args.remote, remote=args.remote_name)
    if args.report:
        _write_markdown_report(report, args.report)
    if args.publish_script:
        _write_publish_script(report, args.publish_script)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 1 if args.strict and not report.ok else 0


if __name__ == "__main__":
    sys.exit(main())
