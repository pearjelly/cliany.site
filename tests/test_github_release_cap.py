from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_github_release_cap", ROOT / "scripts" / "check_github_release_cap.py"
)
assert SPEC and SPEC.loader
release_cap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_cap)


def test_publication_day_uses_shanghai_timezone() -> None:
    releases = [
        {"tagName": "v1", "publishedAt": "2026-10-01T15:58:00Z", "isDraft": False},
        {"tagName": "v2", "publishedAt": "2026-10-01T16:04:00Z", "isDraft": False},
        {"tagName": "v3", "publishedAt": "2026-10-01T17:06:00Z", "isDraft": False},
        {"tagName": "v4", "publishedAt": None, "isDraft": True},
    ]
    assert release_cap._published_tags_today(releases, date(2026, 10, 2)) == ["v2", "v3"]


def test_strict_blocks_at_cap(monkeypatch, capsys) -> None:
    releases = [
        {"tagName": f"v{i}", "publishedAt": "2026-10-01T16:30:00Z", "isDraft": False}
        for i in range(3)
    ]
    monkeypatch.setattr(release_cap, "_fetch_releases", lambda: releases)
    assert release_cap.main(["--today", "2026-10-02", "--strict", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["release_count_today"] == 3
    assert report["daily_release_capacity_remaining"] == 0
    assert report["ok"] is False


def test_strict_allows_next_release_below_cap(monkeypatch, capsys) -> None:
    releases = [{"tagName": "v1", "publishedAt": "2026-10-01T16:30:00Z", "isDraft": False}]
    monkeypatch.setattr(release_cap, "_fetch_releases", lambda: releases)
    assert release_cap.main(["--today", "2026-10-02", "--strict", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["daily_release_capacity_remaining"] == 2
    assert report["ok"] is True


def test_strict_fails_closed_when_remote_unavailable(monkeypatch, capsys) -> None:
    def unavailable():
        raise OSError("gh unavailable")

    monkeypatch.setattr(release_cap, "_fetch_releases", unavailable)
    assert release_cap.main(["--today", "2026-10-02", "--strict", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["release_count_today"] is None
    assert report["error"] == "gh unavailable"


def test_strict_fails_closed_on_invalid_release_data(monkeypatch, capsys) -> None:
    monkeypatch.setattr(release_cap, "_fetch_releases", lambda: [{"tagName": "v1", "isDraft": False}])
    assert release_cap.main(["--today", "2026-10-02", "--strict", "--json"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["release_count_today"] is None
    assert "missing" in report["error"]


def test_tag_release_workflow_checks_cap_before_build() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8"))
    assert workflow["concurrency"] == {"group": "release-publication", "cancel-in-progress": False}
    jobs = workflow["jobs"]
    steps = jobs["release-preflight"]["steps"]
    check = next(step for step in steps if step.get("name") == "Check GitHub publication capacity")
    assert check["run"] == "python scripts/check_github_release_cap.py --strict --json"
    assert check["env"]["GH_TOKEN"] == "${{ github.token }}"
    assert jobs["build"]["needs"] == "release-preflight"
