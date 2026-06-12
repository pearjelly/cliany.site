import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_publication.py"
SPEC = importlib.util.spec_from_file_location("check_release_publication", SCRIPT)
assert SPEC is not None
release_publication = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = release_publication
SPEC.loader.exec_module(release_publication)


def _git(repo: Path, *args: str) -> None:
    subprocess.check_call(["git", *args], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _commit(repo: Path, filename: str, content: str, message: str = "change") -> None:
    path = repo / filename
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", message)


def _init_repo_with_origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    subprocess.check_call(["git", "init", "--bare", origin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["git", "init", "-b", "master", repo], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "remote", "add", "origin", str(origin))
    _commit(repo, "README.md", "# Demo\n", "initial")
    _git(repo, "tag", "v0.1.0")
    _git(repo, "push", "-u", "origin", "master", "--tags")
    return repo


def test_release_publication_passes_when_branch_and_tag_are_pushed(tmp_path):
    repo = _init_repo_with_origin(tmp_path)

    report = release_publication.build_report(repo, remote_check=True)

    assert report.ok is True
    assert report.repo_root == str(repo.resolve())
    assert report.to_dict()["repo_root"] == str(repo.resolve())
    assert report.worktree_clean is True
    assert report.to_dict()["worktree_clean"] is True
    assert report.to_dict()["worktree_status"] == []
    assert report.branch == "master"
    assert report.upstream == "origin/master"
    assert report.latest_tag == "v0.1.0"
    assert report.branch_published is True
    assert report.tag_published is True
    assert report.to_dict()["next_action_count"] == 0
    assert report.to_dict()["next_actions"] == []
    assert report.to_dict()["publish_command_count"] == 0


def test_release_publication_reports_unpushed_release_commit_and_tag(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")

    report = release_publication.build_report(repo)

    assert report.ok is False
    assert report.worktree_clean is True
    assert report.ahead_count == 1
    assert report.latest_tag == "v0.1.1"
    assert report.tag_points_at_head is True
    assert report.tag_commit_in_upstream is False
    assert report.tag_published is False
    assert report.to_dict()["next_action_count"] == 3
    assert report.to_dict()["next_actions"] == [
        "- Push `master` to `origin`; local branch is ahead by `1` commits.",
        (
            "- Push tag `v0.1.1` after the branch is published, or rerun with `--remote` "
            "to verify the live remote tag."
        ),
        "- Rerun with `--remote` when network access is available to verify live remote refs.",
    ]
    assert report.to_dict()["publish_command_count"] == 3
    assert report.to_dict()["publish_commands"] == [
        "git push origin master",
        "git push origin v0.1.1",
        "python scripts/check_release_publication.py --remote --json",
    ]


def test_release_publication_reports_dirty_worktree_before_publish_commands(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    (repo / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")

    report = release_publication.build_report(repo)

    assert report.ok is False
    assert report.worktree_clean is False
    assert report.worktree_status == ["?? scratch.txt"]
    payload = report.to_dict()
    assert payload["worktree_clean"] is False
    assert payload["worktree_status"] == ["?? scratch.txt"]
    assert payload["next_actions"][0] == (
        "- Commit, stash, or discard local worktree changes before publishing release refs."
    )
    assert payload["publish_commands"] == ["python scripts/check_release_publication.py --json"]


def test_release_publication_remote_check_reports_missing_remote_tag(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    _git(repo, "push", "origin", "master")

    report = release_publication.build_report(repo, remote_check=True)

    assert report.ok is False
    assert report.branch_published is True
    assert report.tag_published is False
    assert report.remote_branch_head == report.local_head
    assert report.remote_tag_commit is None
    assert report.to_dict()["next_actions"] == [
        "- Push tag `v0.1.1` to `origin`; remote tag is missing or stale."
    ]
    assert report.to_dict()["publish_commands"] == [
        "git push origin v0.1.1",
        "python scripts/check_release_publication.py --remote --json",
    ]


def test_release_publication_text_output_includes_next_actions(tmp_path, capsys):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    report = release_publication.build_report(repo)

    release_publication._print_text(report)

    output = capsys.readouterr().out
    assert "ok: False" in output
    assert f"repo_root: {repo.resolve()}" in output
    assert "worktree_clean: True" in output
    assert "latest_tag: v0.1.1" in output
    assert "next_action_count: 3" in output
    assert "publish_command_count: 3" in output
    assert output.count("tag_published:") == 1
    assert "next_actions:" in output
    assert "Push `master` to `origin`" in output
    assert "publish_commands:" in output
    assert "git push origin master" in output


def test_release_publication_writes_markdown_report(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    report = release_publication.build_report(repo, remote_check=True)
    report_path = tmp_path / "reports" / "publication.md"

    release_publication._write_markdown_report(report, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "# cliany-site Release Publication" in text
    assert "| ok | `false` |" in text
    assert f"| repo_root | `{repo.resolve()}` |" in text
    assert "| worktree_clean | `true` |" in text
    assert "| latest_tag | `v0.1.1` |" in text
    assert "| remote_checked | `true` |" in text
    assert "| next_action_count | `2` |" in text
    assert "| publish_command_count | `3` |" in text
    assert "## Refs" in text
    assert "## Next Actions" in text
    assert "## Worktree Status" in text
    assert "- Worktree is clean." in text
    assert "## Publish Commands" in text
    assert "git push origin v0.1.1" in text
    assert "python scripts/check_release_publication.py --remote --json" in text
    assert "- Push tag `v0.1.1` to `origin`; remote tag is missing or stale." in text


def test_release_publication_writes_reviewable_publish_script(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    report = release_publication.build_report(repo)
    script_path = tmp_path / "reports" / "publish-release.sh"

    release_publication._write_publish_script(report, script_path)

    text = script_path.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\nset -euo pipefail\n")
    assert "Review these commands before running" in text
    assert "# Publication context:" in text
    assert f"# - repo_root: {repo.resolve()}" in text
    assert "# - branch: master" in text
    assert "# - upstream: origin/master" in text
    assert "# - remote: origin" in text
    assert "# - latest_tag: v0.1.1" in text
    assert f"# - local_head: {report.local_head}" in text
    assert f"# - tag_commit: {report.tag_commit}" in text
    assert "# - ahead_count: 1" in text
    assert "# - behind_count: 0" in text
    assert "# - remote_checked: false" in text
    assert f"REPO_ROOT={repo.resolve()}" in text
    assert 'cd "$REPO_ROOT"' in text
    assert 'CURRENT_REPO_ROOT="$(git rev-parse --show-toplevel)"' in text
    assert f"EXPECTED_LOCAL_HEAD={report.local_head}" in text
    assert "EXPECTED_LATEST_TAG=v0.1.1" in text
    assert f"EXPECTED_TAG_COMMIT={report.tag_commit}" in text
    assert 'CURRENT_LOCAL_HEAD="$(git rev-parse HEAD)"' in text
    assert 'CURRENT_WORKTREE_STATUS="$(git status --porcelain)"' in text
    assert "worktree has uncommitted changes" in text
    assert "Publish script is stale" in text
    assert "git push origin master" in text
    assert "git push origin v0.1.1" in text
    assert "python scripts/check_release_publication.py --remote --json" in text
    assert oct(script_path.stat().st_mode & 0o777) == "0o755"


def test_release_publication_publish_script_rejects_stale_head_before_push(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    origin = tmp_path / "origin.git"
    original_remote_head = subprocess.check_output(
        ["git", "--git-dir", str(origin), "rev-parse", "master"],
        text=True,
    ).strip()
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    report = release_publication.build_report(repo)
    script_path = tmp_path / "reports" / "publish-release.sh"
    release_publication._write_publish_script(report, script_path)

    _commit(repo, "NOTES.md", "new work\n", "new work")
    result = subprocess.run(
        [str(script_path)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Publish script is stale: HEAD is" in result.stderr
    current_remote_head = subprocess.check_output(
        ["git", "--git-dir", str(origin), "rev-parse", "master"],
        text=True,
    ).strip()
    assert current_remote_head == original_remote_head


def test_release_publication_publish_script_rejects_dirty_worktree_before_push(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    origin = tmp_path / "origin.git"
    original_remote_head = subprocess.check_output(
        ["git", "--git-dir", str(origin), "rev-parse", "master"],
        text=True,
    ).strip()
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    report = release_publication.build_report(repo)
    script_path = tmp_path / "reports" / "publish-release.sh"
    release_publication._write_publish_script(report, script_path)

    (repo / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    result = subprocess.run(
        [str(script_path)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Publish script is stale: worktree has uncommitted changes." in result.stderr
    assert "scratch.txt" in result.stderr
    current_remote_head = subprocess.check_output(
        ["git", "--git-dir", str(origin), "rev-parse", "master"],
        text=True,
    ).strip()
    assert current_remote_head == original_remote_head


def test_release_publication_main_writes_report_with_json(tmp_path, monkeypatch, capsys):
    repo = _init_repo_with_origin(tmp_path)
    report_path = tmp_path / "publication.md"
    script_path = tmp_path / "publish-release.sh"
    monkeypatch.setattr(release_publication, "ROOT", repo)

    exit_code = release_publication.main(
        ["--json", "--report", str(report_path), "--publish-script", str(script_path)]
    )

    payload = capsys.readouterr().out
    assert exit_code == 0
    assert '"ok": true' in payload
    assert report_path.exists()
    assert "| ok | `true` |" in report_path.read_text(encoding="utf-8")
    assert script_path.exists()
    assert "python scripts/check_release_publication.py --remote --json" in script_path.read_text(encoding="utf-8")
