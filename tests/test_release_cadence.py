import importlib.util
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release_cadence.py"
SPEC = importlib.util.spec_from_file_location("check_release_cadence", SCRIPT)
assert SPEC is not None
release_cadence = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = release_cadence
SPEC.loader.exec_module(release_cadence)


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.check_call(["git", *args], cwd=repo, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _commit(repo: Path, filename: str, content: str, day: str) -> None:
    path = repo / filename
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": f"{day}T12:00:00+00:00",
        "GIT_COMMITTER_DATE": f"{day}T12:00:00+00:00",
    }
    _git(repo, "commit", "-m", f"test {day}", env=env)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8")
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n"
        "- Pending release note.\n\n"
        "## [0.1.0] - 2026-06-01\n\n"
        "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD\n",
        encoding="utf-8",
    )
    _git(repo, "add", "pyproject.toml", "CHANGELOG.md")
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2026-06-08T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-06-08T12:00:00+00:00",
    }
    _git(repo, "commit", "-m", "initial", env=env)
    _git(repo, "tag", "v0.1.0")
    return repo


def test_release_cadence_report_passes_with_three_commit_days(tmp_path):
    repo = _init_repo(tmp_path)
    _commit(repo, "a.txt", "a", "2026-06-09")
    _commit(repo, "b.txt", "b", "2026-06-10")

    report = release_cadence.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    assert report.ok is True
    assert report.version == "0.1.0"
    assert report.latest_tag == "v0.1.0"
    assert report.tag_matches_version is True
    assert report.commit_days == ["2026-06-08", "2026-06-09", "2026-06-10"]
    assert report.commits_since_latest_tag == 2
    assert report.changelog_unreleased_has_content is True
    assert report.changelog_unreleased_compare_ok is True
    assert (
        report.changelog_unreleased_compare_expected
        == "https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD"
    )
    assert report.changelog_unreleased_compare_actual == report.changelog_unreleased_compare_expected
    assert report.dirty is False
    assert report.to_dict()["missing_commit_days"] == 0
    assert report.to_dict()["next_actions"] == []


def test_release_cadence_report_fails_when_week_has_too_few_days(tmp_path):
    repo = _init_repo(tmp_path)

    report = release_cadence.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    assert report.ok is False
    assert report.commit_day_count == 1
    assert report.min_commit_days == 3
    assert report.to_dict()["missing_commit_days"] == 2
    assert report.to_dict()["next_actions"] == [
        "- Ship verified slices on `2` more unique commit days this week; current commit days are `1/3`."
    ]


def test_release_cadence_allows_empty_unreleased_when_head_is_tagged(tmp_path):
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [0.1.0] - 2026-06-08\n"
        "- Released.\n\n"
        "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD\n",
        encoding="utf-8",
    )
    _git(repo, "add", "CHANGELOG.md")
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2026-06-08T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-06-08T12:00:00+00:00",
    }
    _git(repo, "commit", "--amend", "--no-edit", env=env)
    _git(repo, "tag", "-f", "v0.1.0")

    report = release_cadence.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is True
    assert report.commits_since_latest_tag == 0
    assert report.changelog_unreleased_has_content is False
    assert report.changelog_ok is True


def test_release_cadence_fails_when_unreleased_compare_link_is_stale(tmp_path):
    repo = _init_repo(tmp_path)
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n"
        "- Pending release note.\n\n"
        "## [0.1.0] - 2026-06-01\n\n"
        "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.0.9...HEAD\n",
        encoding="utf-8",
    )
    _git(repo, "add", "CHANGELOG.md")
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2026-06-08T12:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-06-08T12:00:00+00:00",
    }
    _git(repo, "commit", "--amend", "--no-edit", env=env)
    _git(repo, "tag", "-f", "v0.1.0")

    report = release_cadence.build_report(repo, today=date(2026, 6, 10), min_commit_days=1)

    assert report.ok is False
    assert report.changelog_unreleased_compare_ok is False
    assert (
        report.changelog_unreleased_compare_expected
        == "https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD"
    )
    assert (
        report.changelog_unreleased_compare_actual
        == "https://github.com/pearjelly/cliany.site/compare/v0.0.9...HEAD"
    )
    assert report.to_dict()["next_actions"] == [
        (
            "- Update the CHANGELOG `[Unreleased]` compare link to "
            "`https://github.com/pearjelly/cliany.site/compare/v0.1.0...HEAD`."
        )
    ]


def test_release_cadence_text_output_includes_next_actions_when_blocked(tmp_path, capsys):
    repo = _init_repo(tmp_path)
    report = release_cadence.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    release_cadence._print_text(report)

    output = capsys.readouterr().out
    assert "ok: False" in output
    assert "next_actions:" in output
    assert "- Ship verified slices on `2` more unique commit days this week" in output


def test_release_cadence_text_output_omits_next_actions_when_ready(tmp_path, capsys):
    repo = _init_repo(tmp_path)
    _commit(repo, "a.txt", "a", "2026-06-09")
    _commit(repo, "b.txt", "b", "2026-06-10")
    report = release_cadence.build_report(repo, today=date(2026, 6, 10), min_commit_days=3)

    release_cadence._print_text(report)

    output = capsys.readouterr().out
    assert "ok: True" in output
    assert "next_actions:" not in output
