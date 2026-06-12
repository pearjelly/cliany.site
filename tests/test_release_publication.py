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
    assert report.branch == "master"
    assert report.upstream == "origin/master"
    assert report.latest_tag == "v0.1.0"
    assert report.branch_published is True
    assert report.tag_published is True
    assert report.to_dict()["next_actions"] == []


def test_release_publication_reports_unpushed_release_commit_and_tag(tmp_path):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")

    report = release_publication.build_report(repo)

    assert report.ok is False
    assert report.ahead_count == 1
    assert report.latest_tag == "v0.1.1"
    assert report.tag_points_at_head is True
    assert report.tag_commit_in_upstream is False
    assert report.tag_published is False
    assert report.to_dict()["next_actions"] == [
        "- Push `master` to `origin`; local branch is ahead by `1` commits.",
        (
            "- Push tag `v0.1.1` after the branch is published, or rerun with `--remote` "
            "to verify the live remote tag."
        ),
        "- Rerun with `--remote` when network access is available to verify live remote refs.",
    ]


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


def test_release_publication_text_output_includes_next_actions(tmp_path, capsys):
    repo = _init_repo_with_origin(tmp_path)
    _commit(repo, "CHANGELOG.md", "released\n", "release")
    _git(repo, "tag", "v0.1.1")
    report = release_publication.build_report(repo)

    release_publication._print_text(report)

    output = capsys.readouterr().out
    assert "ok: False" in output
    assert "latest_tag: v0.1.1" in output
    assert "next_actions:" in output
    assert "Push `master` to `origin`" in output
