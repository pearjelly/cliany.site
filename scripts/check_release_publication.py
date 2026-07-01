#!/usr/bin/env python3
"""Check whether the latest local release is visible from the configured upstream."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DistributionReport:
    checked: bool
    ok: bool
    expected_tag: str | None
    expected_version: str | None
    github_repo: str | None
    github_release_tag: str | None
    github_release_published: bool | None
    pypi_project: str | None
    pypi_version: str | None
    pypi_latest_version: str | None
    pypi_release_version: str | None
    pypi_published: bool | None
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        next_actions = _distribution_next_actions(self)
        return {
            "checked": self.checked,
            "ok": self.ok,
            "expected_tag": self.expected_tag,
            "expected_version": self.expected_version,
            "github_repo": self.github_repo,
            "github_release_tag": self.github_release_tag,
            "github_release_published": self.github_release_published,
            "pypi_project": self.pypi_project,
            "pypi_version": self.pypi_version,
            "pypi_latest_version": self.pypi_latest_version,
            "pypi_release_version": self.pypi_release_version,
            "pypi_published": self.pypi_published,
            "issues": self.issues,
            "next_action_count": len(next_actions),
            "next_actions_sha256": _stable_json_sha256(next_actions),
            "primary_next_action": next_actions[0] if next_actions else None,
            "next_actions": next_actions,
        }


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
    remote_check_ok: bool | None
    remote_check_issues: list[str]
    remote_branch_head: str | None
    remote_tag_commit: str | None
    branch_published: bool | None
    tag_published: bool | None
    distribution: DistributionReport

    def to_dict(self) -> dict[str, Any]:
        next_actions = _next_action_lines(self)
        publish_commands = _publish_command_lines(self)
        tag_publish_decision = _tag_publish_decision(self)
        distribution_payload = self.distribution.to_dict()
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
            "remote_check_ok": self.remote_check_ok,
            "remote_check_issues": self.remote_check_issues,
            "remote_branch_head": self.remote_branch_head,
            "remote_tag_commit": self.remote_tag_commit,
            "branch_published": self.branch_published,
            "tag_published": self.tag_published,
            "distribution_checked": self.distribution.checked,
            "distribution_ok": self.distribution.ok,
            "distribution": distribution_payload,
            "tag_publish_decision": tag_publish_decision,
            "next_action_count": len(next_actions),
            "next_actions_sha256": _stable_json_sha256(next_actions),
            "primary_next_action": next_actions[0] if next_actions else None,
            "next_actions": next_actions,
            "publish_command_count": len(publish_commands),
            "publish_commands_sha256": _stable_json_sha256(publish_commands),
            "primary_publish_command": publish_commands[0] if publish_commands else None,
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


def _ls_remote_ref(root: Path, remote: str, ref: str) -> tuple[str | None, str | None]:
    try:
        output = _run_git(["ls-remote", remote, ref], root)
    except subprocess.CalledProcessError:
        return None, f"Remote ref check failed for `{ref}` on `{remote}`."
    if not output:
        return None, None
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0], None
    return None, None


def _worktree_status(root: Path) -> list[str]:
    status = _optional_git(["status", "--porcelain"], root)
    return status.splitlines() if status else []


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "cliany-site-release-audit",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _project_metadata(root: Path) -> dict[str, Any]:
    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8")).get("project") or {}


def _infer_pypi_project(root: Path) -> str | None:
    project = _project_metadata(root)
    name = project.get("name")
    return str(name) if name else None


def _github_repo_from_url(url: str) -> str | None:
    cleaned = url.rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    if cleaned.startswith("git@github.com:"):
        return cleaned.split(":", 1)[1]
    parsed = urllib.parse.urlparse(cleaned)
    if parsed.netloc.lower() != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    return "/".join(parts[:2])


def _infer_github_repo(root: Path) -> str | None:
    project = _project_metadata(root)
    urls = project.get("urls") or {}
    repository = urls.get("Repository")
    if repository:
        repo = _github_repo_from_url(str(repository))
        if repo:
            return repo
    remote_url = _optional_git(["remote", "get-url", "origin"], root)
    return _github_repo_from_url(remote_url) if remote_url else None


def _build_distribution_report(
    root: Path,
    *,
    checked: bool,
    latest_tag: str | None,
    github_repo: str | None = None,
    pypi_project: str | None = None,
) -> DistributionReport:
    expected_version = latest_tag[1:] if latest_tag and latest_tag.startswith("v") else latest_tag
    if not checked:
        return DistributionReport(
            checked=False,
            ok=True,
            expected_tag=latest_tag,
            expected_version=expected_version,
            github_repo=github_repo,
            github_release_tag=None,
            github_release_published=None,
            pypi_project=pypi_project,
            pypi_version=None,
            pypi_latest_version=None,
            pypi_release_version=None,
            pypi_published=None,
            issues=[],
        )

    resolved_github_repo = github_repo or _infer_github_repo(root)
    resolved_pypi_project = pypi_project or _infer_pypi_project(root)
    issues: list[str] = []
    github_release_tag = None
    github_release_published = None
    pypi_version = None
    pypi_latest_version = None
    pypi_release_version = None
    pypi_published = None

    if not latest_tag:
        issues.append("release tag is missing; cannot check public distribution artifacts")

    if not resolved_github_repo:
        issues.append("GitHub repository could not be inferred; pass --github-repo")
    elif latest_tag:
        try:
            github_payload = _fetch_json(f"https://api.github.com/repos/{resolved_github_repo}/releases/latest")
            github_release_tag = str(github_payload.get("tag_name") or "")
            github_release_published = (
                github_release_tag == latest_tag
                and github_payload.get("draft") is False
                and github_payload.get("prerelease") is False
            )
            if not github_release_published:
                issues.append(
                    f"GitHub Release latest tag {github_release_tag or '(missing)'} != {latest_tag}"
                )
        except Exception as exc:  # noqa: BLE001 - report network/API failures as audit evidence.
            issues.append(f"GitHub Release check failed: {exc}")

    if not resolved_pypi_project:
        issues.append("PyPI project could not be inferred; pass --pypi-project")
    elif expected_version:
        try:
            project_part = urllib.parse.quote(resolved_pypi_project, safe="")
            version_part = urllib.parse.quote(expected_version, safe="")
            pypi_payload = _fetch_json(f"https://pypi.org/pypi/{project_part}/json")
            info = pypi_payload.get("info") or {}
            pypi_latest_version = str(info.get("version") or "")
            if pypi_latest_version == expected_version:
                pypi_version = expected_version
                pypi_release_version = expected_version
                pypi_published = True
            else:
                try:
                    release_payload = _fetch_json(
                        f"https://pypi.org/pypi/{project_part}/{version_part}/json"
                    )
                    release_info = release_payload.get("info") or {}
                    release_files = release_payload.get("urls") or []
                    pypi_release_version = str(release_info.get("version") or "")
                    pypi_published = pypi_release_version == expected_version and bool(release_files)
                    pypi_version = pypi_release_version if pypi_published else pypi_latest_version
                    if not pypi_published:
                        issues.append(
                            "PyPI latest version "
                            f"{pypi_latest_version or '(missing)'} != {expected_version}; "
                            "version URL did not expose published files"
                        )
                except Exception as exc:  # noqa: BLE001 - report network/API failures as audit evidence.
                    pypi_version = pypi_latest_version
                    pypi_published = False
                    issues.append(
                        "PyPI latest version "
                        f"{pypi_latest_version or '(missing)'} != {expected_version}; "
                        f"version URL check failed: {exc}"
                    )
        except Exception as exc:  # noqa: BLE001 - report network/API failures as audit evidence.
            issues.append(f"PyPI check failed: {exc}")

    return DistributionReport(
        checked=True,
        ok=not issues,
        expected_tag=latest_tag,
        expected_version=expected_version,
        github_repo=resolved_github_repo,
        github_release_tag=github_release_tag,
        github_release_published=github_release_published,
        pypi_project=resolved_pypi_project,
        pypi_version=pypi_version,
        pypi_latest_version=pypi_latest_version,
        pypi_release_version=pypi_release_version,
        pypi_published=pypi_published,
        issues=issues,
    )


def build_report(
    root: Path = ROOT,
    *,
    remote_check: bool = False,
    remote: str = "origin",
    distribution_check: bool = False,
    github_repo: str | None = None,
    pypi_project: str | None = None,
) -> PublicationReport:
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
    remote_check_ok = None
    remote_check_issues: list[str] = []
    branch_published = ahead_count == 0 if ahead_count is not None else None
    tag_published = tag_commit_in_upstream

    if remote_check:
        remote_check_ok = True
        if branch:
            remote_branch_head, branch_issue = _ls_remote_ref(
                root, remote_name, f"refs/heads/{branch}"
            )
            if branch_issue:
                remote_check_issues.append(branch_issue)
        if latest_tag:
            remote_tag_commit, tag_issue = _ls_remote_ref(
                root, remote_name, f"refs/tags/{latest_tag}"
            )
            if tag_issue:
                remote_check_issues.append(tag_issue)
        remote_check_ok = not remote_check_issues
        if remote_check_ok:
            branch_published = bool(local_head and remote_branch_head == local_head)
            tag_published = bool(tag_commit and remote_tag_commit == tag_commit)

    distribution = _build_distribution_report(
        root,
        checked=distribution_check,
        latest_tag=latest_tag,
        github_repo=github_repo,
        pypi_project=pypi_project,
    )

    refs_ok = bool(
        branch_published is True
        and tag_published is True
        and tag_points_at_head
        and worktree_clean
        and latest_tag
        and remote_check_ok is not False
    )
    ok = refs_ok and distribution.ok

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
        remote_check_ok=remote_check_ok,
        remote_check_issues=remote_check_issues,
        remote_branch_head=remote_branch_head,
        remote_tag_commit=remote_tag_commit,
        branch_published=branch_published,
        tag_published=tag_published,
        distribution=distribution,
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
    elif report.remote_check_ok is False:
        actions.append("Remote ref check failed; rerun with `--remote` after network access is available.")
    actions.extend(report.distribution.to_dict()["next_actions"])
    return actions


def _distribution_next_actions(report: DistributionReport) -> list[str]:
    if not report.checked or report.ok:
        return []

    actions: list[str] = []
    for issue in report.issues:
        if issue.startswith("GitHub Release latest tag"):
            actions.append(
                f"Wait for or repair GitHub Release `{report.expected_tag}` before considering the release complete."
            )
        elif issue.startswith("PyPI latest version"):
            actions.append(
                f"Wait for or repair PyPI version `{report.expected_version}` before considering the release complete."
            )
        elif issue.startswith("GitHub Release check failed") or issue.startswith("PyPI check failed"):
            action = "Rerun with `--distribution` after network/API access is available."
            if action not in actions:
                actions.append(action)
        else:
            actions.append(issue)
    return actions


def _publish_command_lines(report: PublicationReport) -> list[str]:
    if not report.worktree_clean:
        return ["python scripts/check_release_publication.py --json"]
    if report.remote_check_ok is False:
        return ["python scripts/check_release_publication.py --remote --json"]

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


def _stable_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    if report.remote_check_ok is False:
        return {
            "status": "needs_remote_check",
            "can_push_tag": False,
            "latest_tag": report.latest_tag,
            "tag_points_at_head": True,
            "tag_published": report.tag_published,
            "required_action": "Rerun with `--remote` to verify the live remote tag.",
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
    print(f"distribution_checked: {report.distribution.checked}")
    print(f"distribution_ok: {report.distribution.ok}")
    print(f"tag_publish_decision: {tag_publish_decision['status']}")
    print(f"remote_checked: {report.remote_checked}")
    print(f"remote_check_ok: {report.remote_check_ok}")
    print(f"next_action_count: {len(next_actions)}")
    print(f"next_actions_sha256: {_stable_json_sha256(next_actions)}")
    print(f"primary_next_action: {next_actions[0] if next_actions else '(none)'}")
    print(f"publish_command_count: {len(publish_commands)}")
    print(f"publish_commands_sha256: {_stable_json_sha256(publish_commands)}")
    print(f"primary_publish_command: {publish_commands[0] if publish_commands else '(none)'}")
    if report.worktree_status:
        print("worktree_status:")
        for line in report.worktree_status:
            print(f"- {line}")
    if report.remote_check_issues:
        print("remote_check_issues:")
        for issue in report.remote_check_issues:
            print(f"- {issue}")
    if report.distribution.checked:
        print("distribution:")
        print(f"- github_repo: {report.distribution.github_repo or '(none)'}")
        print(f"- github_release_tag: {report.distribution.github_release_tag or '(none)'}")
        print(f"- github_release_published: {report.distribution.github_release_published}")
        print(f"- pypi_project: {report.distribution.pypi_project or '(none)'}")
        print(f"- pypi_version: {report.distribution.pypi_version or '(none)'}")
        print(f"- pypi_latest_version: {report.distribution.pypi_latest_version or '(none)'}")
        print(f"- pypi_release_version: {report.distribution.pypi_release_version or '(none)'}")
        print(f"- pypi_published: {report.distribution.pypi_published}")
        if report.distribution.issues:
            print("- issues:")
            for issue in report.distribution.issues:
                print(f"  - {issue}")
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
        f"| distribution_checked | `{_format_bool(report.distribution.checked)}` |",
        f"| distribution_ok | `{_format_bool(report.distribution.ok)}` |",
        f"| tag_publish_decision | `{tag_publish_decision['status']}` |",
        f"| tag_can_push | `{_format_bool(tag_publish_decision['can_push_tag'])}` |",
        f"| remote_checked | `{_format_bool(report.remote_checked)}` |",
        f"| remote_check_ok | `{_format_bool(report.remote_check_ok)}` |",
        f"| next_action_count | `{len(next_actions)}` |",
        f"| next_actions_sha256 | `{_stable_json_sha256(next_actions)}` |",
        f"| primary_next_action | `{_format_value(next_actions[0] if next_actions else None)}` |",
        f"| publish_command_count | `{len(publish_commands)}` |",
        f"| publish_commands_sha256 | `{_stable_json_sha256(publish_commands)}` |",
        f"| primary_publish_command | `{_format_value(publish_commands[0] if publish_commands else None)}` |",
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
    if report.remote_check_issues:
        lines.extend(
            [
                "",
                "## Remote Check Issues",
                "",
                *(f"- {issue}" for issue in report.remote_check_issues),
            ]
        )
    if report.distribution.checked:
        lines.extend(
            [
                "",
                "## Distribution Visibility",
                "",
                f"- expected_tag: `{_format_value(report.distribution.expected_tag)}`",
                f"- expected_version: `{_format_value(report.distribution.expected_version)}`",
                f"- github_repo: `{_format_value(report.distribution.github_repo)}`",
                f"- github_release_tag: `{_format_value(report.distribution.github_release_tag)}`",
                f"- github_release_published: `{_format_bool(report.distribution.github_release_published)}`",
                f"- pypi_project: `{_format_value(report.distribution.pypi_project)}`",
                f"- pypi_version: `{_format_value(report.distribution.pypi_version)}`",
                f"- pypi_latest_version: `{_format_value(report.distribution.pypi_latest_version)}`",
                f"- pypi_release_version: `{_format_value(report.distribution.pypi_release_version)}`",
                f"- pypi_published: `{_format_bool(report.distribution.pypi_published)}`",
            ]
        )
        if report.distribution.issues:
            lines.extend(["", "### Distribution Issues", "", *(f"- {issue}" for issue in report.distribution.issues)])
    if publish_commands:
        lines.extend(["", "## Publish Commands", "", "```bash", *publish_commands, "```"])
    else:
        lines.extend(["", "## Publish Commands", "", "- No publish commands are needed."])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_publish_script(report: PublicationReport, path: Path) -> None:
    commands = _publish_command_lines(report)
    next_actions = _next_action_lines(report)
    expected_next_actions_sha256 = _stable_json_sha256(next_actions)
    expected_publish_commands_sha256 = _stable_json_sha256(commands)
    repo_root = report.repo_root
    expected_local_head = report.local_head or ""
    expected_latest_tag = report.latest_tag or ""
    expected_tag_commit = report.tag_commit or ""
    python_bin = sys.executable or "python"
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
        f"# - next_action_count: {len(next_actions)}",
        f"# - next_actions_sha256: {expected_next_actions_sha256}",
        f"# - primary_next_action: {_format_value(next_actions[0] if next_actions else None)}",
        f"# - publish_command_count: {len(commands)}",
        f"# - publish_commands_sha256: {expected_publish_commands_sha256}",
        f"# - primary_publish_command: {_format_value(commands[0] if commands else None)}",
        *_publish_script_review_notes(report),
        "",
        f"REPO_ROOT={shlex.quote(repo_root)}",
        f"EXPECTED_LOCAL_HEAD={shlex.quote(expected_local_head)}",
        f"EXPECTED_LATEST_TAG={shlex.quote(expected_latest_tag)}",
        f"EXPECTED_TAG_COMMIT={shlex.quote(expected_tag_commit)}",
        f"EXPECTED_NEXT_ACTIONS_SHA256={shlex.quote(expected_next_actions_sha256)}",
        f"EXPECTED_PUBLISH_COMMANDS_SHA256={shlex.quote(expected_publish_commands_sha256)}",
        f"PYTHON_BIN={shlex.quote(python_bin)}",
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
        "extract_publication_field() {",
        "  \"$PYTHON_BIN\" -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' \"$1\"",
        "}",
        f'CURRENT_PUBLICATION_JSON="$("$PYTHON_BIN" {_publish_script_audit_command(report)})"',
        'CURRENT_NEXT_ACTIONS_SHA256="$(printf "%s\\n" "$CURRENT_PUBLICATION_JSON" '
        '| extract_publication_field next_actions_sha256)"',
        'CURRENT_PUBLISH_COMMANDS_SHA256="$(printf "%s\\n" "$CURRENT_PUBLICATION_JSON" '
        '| extract_publication_field publish_commands_sha256)"',
        'if [[ "$CURRENT_NEXT_ACTIONS_SHA256" != "$EXPECTED_NEXT_ACTIONS_SHA256" ]]; then',
        '  echo "Publish script is stale: publication next actions changed." >&2',
        '  echo "Current next_actions_sha256: $CURRENT_NEXT_ACTIONS_SHA256" >&2',
        '  echo "Expected next_actions_sha256: $EXPECTED_NEXT_ACTIONS_SHA256" >&2',
        "  exit 1",
        "fi",
        'if [[ "$CURRENT_PUBLISH_COMMANDS_SHA256" != "$EXPECTED_PUBLISH_COMMANDS_SHA256" ]]; then',
        '  echo "Publish script is stale: publication publish commands changed." >&2',
        '  echo "Current publish_commands_sha256: $CURRENT_PUBLISH_COMMANDS_SHA256" >&2',
        '  echo "Expected publish_commands_sha256: $EXPECTED_PUBLISH_COMMANDS_SHA256" >&2',
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


def _publish_script_audit_command(report: PublicationReport) -> str:
    parts = ["scripts/check_release_publication.py"]
    if report.remote_checked:
        parts.append("--remote")
    if report.distribution.checked:
        parts.append("--distribution")
        if report.distribution.github_repo:
            parts.extend(["--github-repo", report.distribution.github_repo])
        if report.distribution.pypi_project:
            parts.extend(["--pypi-project", report.distribution.pypi_project])
    parts.append("--json")
    return " ".join(shlex.quote(part) for part in parts)


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
    parser.add_argument(
        "--distribution",
        action="store_true",
        help="Check public GitHub Release and PyPI visibility for the latest local tag.",
    )
    parser.add_argument("--github-repo", help="GitHub repository slug, e.g. pearjelly/cliany.site.")
    parser.add_argument("--pypi-project", help="PyPI project name, e.g. cliany-site.")
    parser.add_argument("--report", type=Path, help="Write a Markdown publication report to this path.")
    parser.add_argument("--publish-script", type=Path, help="Write a reviewable shell script with publish commands.")
    args = parser.parse_args(argv)

    report = build_report(
        ROOT,
        remote_check=args.remote,
        remote=args.remote_name,
        distribution_check=args.distribution,
        github_repo=args.github_repo,
        pypi_project=args.pypi_project,
    )
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
