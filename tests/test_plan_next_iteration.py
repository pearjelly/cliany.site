import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SCRIPT = SCRIPTS / "plan_next_iteration.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("plan_next_iteration", SCRIPT)
assert SPEC is not None
plan_next_iteration = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = plan_next_iteration
SPEC.loader.exec_module(plan_next_iteration)


def _write_pyproject(root: Path, version: str = "0.16.1") -> None:
    (root / "pyproject.toml").write_text(
        f"""
[project]
name = "cliany-site"
version = "{version}"
""",
        encoding="utf-8",
    )


def _readiness_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=False,
        target_version="0.16.2",
        blockers=["release draft validation failed"],
        min_case_assets=8,
        draft=SimpleNamespace(
            ok=False,
            path="/tmp/project/docs/releases/v0.16.2-draft.md",
            target_version="0.16.2",
            issues=[
                "release draft is missing",
                "release draft missing snippet: ## 发版前验证",
            ],
        ),
        cadence=SimpleNamespace(
            commit_day_count=2,
            min_commit_days=3,
        ),
        cases=SimpleNamespace(
            active=4,
            candidate=3,
            known_gap=1,
            total=8,
            cases=[
                SimpleNamespace(
                    id="pypi-project-search",
                    status="candidate",
                    target_url="https://pypi.org/search/?q=cliany-site",
                    commands=[
                        'cliany-site explore "https://pypi.org" "search Python packages" --json',
                        "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json",
                    ],
                    offline_commands=[
                        "python scripts/validate_cases.py --strict",
                        "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md",
                    ],
                    promotion={
                        "adapter_package": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
                        "metadata_validation": "Run validate_cases with --packages-dir.",
                        "online_smoke": "Run read-only PyPI search smoke.",
                    },
                ),
                SimpleNamespace(
                    id="npm-package-search",
                    status="candidate",
                    target_url="https://www.npmjs.com/search?q=playwright",
                    commands=[
                        "cliany-site www.npmjs.com search-packages --query playwright --limit 5 --json",
                    ],
                    offline_commands=["python scripts/validate_cases.py --strict"],
                    promotion={
                        "adapter_package": "Generate www.npmjs.com-<version>.cliany-adapter.tar.gz.",
                        "metadata_validation": "Run validate_cases with --packages-dir.",
                        "online_smoke": "Run read-only npm search smoke.",
                    },
                ),
                SimpleNamespace(id="search-extraction-gap", status="known-gap"),
            ],
        ),
    )


def _publication_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=False,
        repo_root="/repo/cliany.site",
        branch="master",
        upstream="origin/master",
        remote="origin",
        local_head="abc123",
        upstream_head="def456",
        ahead_count=2,
        behind_count=0,
        latest_tag="v0.16.1",
        tag_commit="abc123",
        remote_checked=False,
        tag_published=False,
        worktree_clean=False,
        worktree_status=[" M CHANGELOG.md"],
        next_actions=[
            "- Commit, stash, or discard local worktree changes before publishing release refs.",
            "- Push `master` to `origin`; local branch is ahead by `2` commits.",
            "- Push tag `v0.16.1` after the branch is published.",
        ],
        publish_commands=[
            "python scripts/check_release_publication.py --json",
        ],
    )


def test_plan_defaults_to_next_patch_version(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )

    assert plan.current_version == "0.16.1"
    assert plan.target_version == "0.16.2"
    assert plan.recommended_theme == "发布可见性"
    assert "latest local release is not published" in plan.blockers
    assert plan.candidate_cases == ["pypi-project-search", "npm-package-search"]
    assert plan.candidate_promotions[0].case_id == "pypi-project-search"


def test_plan_json_keeps_actionable_validation_commands(tmp_path):
    _write_pyproject(tmp_path)

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )
    data = plan.to_dict()

    assert data["release_draft_path"] == "docs/releases/v0.16.2-draft.md"
    assert data["release_draft_issues"] == [
        "release draft is missing",
        "release draft missing snippet: ## 发版前验证",
    ]
    assert "python scripts/check_release_publication.py --json" in data["validation_commands"]
    assert "python scripts/validate_cases.py --strict" in data["validation_commands"]
    assert (
        data["issue_artifacts_command"]
        == "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--issues-dir /tmp/cliany-candidate-issues"
    )
    assert data["publication_publish_commands"] == [
        "python scripts/check_release_publication.py --json",
    ]
    assert data["publication_visibility"] == {
        "status": "dirty_worktree",
        "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
    }
    assert data["publication_ref_context"] == {
        "repo_root": "/repo/cliany.site",
        "branch": "master",
        "upstream": "origin/master",
        "remote": "origin",
        "local_head": "abc123",
        "upstream_head": "def456",
        "ahead_count": 2,
        "behind_count": 0,
        "latest_tag": "v0.16.1",
        "tag_commit": "abc123",
        "remote_checked": False,
    }
    assert data["publication_worktree_clean"] is False
    assert data["publication_worktree_status"] == [" M CHANGELOG.md"]
    assert (
        data["publication_publish_script_command"]
        == "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    )
    assert data["publication_next_actions"] == [
        "Commit, stash, or discard local worktree changes before publishing release refs.",
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
        "Push tag `v0.16.1` after the branch is published.",
    ]
    assert any("push `master`" in action for action in data["next_actions"])
    assert data["candidate_promotions"][0] == {
        "case_id": "pypi-project-search",
        "issue_title": "Promote candidate case `pypi-project-search` toward active",
        "issue_labels": ["case-proposal", "good first issue"],
        "target_url": "https://pypi.org/search/?q=cliany-site",
        "commands": [
            'cliany-site explore "https://pypi.org" "search Python packages" --json',
            "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json",
        ],
        "offline_commands": [
            "python scripts/validate_cases.py --strict",
            "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md",
        ],
        "adapter_package": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        "metadata_validation": "Run validate_cases with --packages-dir.",
        "online_smoke": "Run read-only PyPI search smoke.",
        "issue_body": (
            "## Scope: promote candidate case `pypi-project-search`\n\n"
            "Move this candidate case one step closer to `active` without changing its status early.\n\n"
            "## Reproduction Context\n"
            "- Target URL: https://pypi.org/search/?q=cliany-site\n"
            "- Candidate commands:\n"
            '  - `cliany-site explore "https://pypi.org" "search Python packages" --json`\n'
            "  - `cliany-site pypi.org search-projects --query cliany-site --limit 5 --json`\n"
            "- Offline validation commands:\n"
            "  - `python scripts/validate_cases.py --strict`\n"
            "  - `python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md`\n\n"
            "## Tasks\n"
            "- [ ] `adapter_package`: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "- [ ] `metadata_validation`: Run validate_cases with --packages-dir.\n"
            "- [ ] `online_smoke`: Run read-only PyPI search smoke.\n\n"
            "## Validation Evidence\n"
            "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.\n"
            "- Paste the local `scripts/validate_cases.py --packages-dir` result.\n"
            "- Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`.\n\n"
            "## Non-goals\n"
            "- Do not mark the case `active` until all three promotion tasks are complete.\n"
            "- Do not require real LLM keys or write runtime state into the repository."
        ),
    }


def test_plan_markdown_report_includes_candidate_promotion_tasks(tmp_path):
    _write_pyproject(tmp_path)
    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )
    report_path = tmp_path / "reports" / "next-iteration.md"

    plan_next_iteration._write_markdown_report(plan, report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "## Candidate Issue Metadata" in text
    assert "| `pypi-project-search` | Promote candidate case `pypi-project-search` toward active |" in text
    assert "`case-proposal`, `good first issue`" in text
    assert "## Candidate Promotion Tasks" in text
    assert "## Candidate Issue Body Templates" in text
    assert "## Publication Publish Commands" in text
    assert "## Publication Visibility" in text
    assert "status: `dirty_worktree`" in text
    assert "Worktree has uncommitted changes; resolve them before publishing release refs." in text
    assert "## Publication Next Actions" in text
    assert "## Publication Ref Context" in text
    assert "| latest_tag | `v0.16.1` |" in text
    assert "| local_head | `abc123` |" in text
    assert "| remote_checked | `false` |" in text
    assert "## Publication Worktree" in text
    assert "worktree_clean: `false`" in text
    assert " M CHANGELOG.md" in text
    assert "Commit, stash, or discard local worktree changes" in text
    assert "Push `master` to `origin`; local branch is ahead by `2` commits." in text
    assert "Push tag `v0.16.1` after the branch is published." in text
    assert "python scripts/check_release_publication.py --json" in text
    assert "## Publication Publish Script" in text
    assert "python scripts/check_release_publication.py --json --publish-script /tmp/cliany-publish-release.sh" in text
    assert "## Release Draft" in text
    assert "`docs/releases/v0.16.2-draft.md`" in text
    assert "### Release Draft Issues" in text
    assert "release draft is missing" in text
    assert "release draft missing snippet: ## 发版前验证" in text
    assert "| `pypi-project-search` | Generate pypi.org-<version>.cliany-adapter.tar.gz." in text
    assert "## Scope: promote candidate case `pypi-project-search`" in text
    assert "## Reproduction Context" in text
    assert "- Target URL: https://pypi.org/search/?q=cliany-site" in text
    assert 'cliany-site explore "https://pypi.org" "search Python packages" --json' in text
    assert "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md" in text
    assert "Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`." in text
    assert "Run read-only npm search smoke." in text


def test_plan_writes_candidate_issue_files(tmp_path):
    _write_pyproject(tmp_path)
    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )
    issues_dir = tmp_path / "issue-artifacts"

    plan_next_iteration._write_candidate_issue_files(plan, issues_dir)

    body = (issues_dir / "pypi-project-search.md").read_text(encoding="utf-8")
    metadata = json.loads((issues_dir / "issue-metadata.json").read_text(encoding="utf-8"))
    publication_handoff = json.loads((issues_dir / "publication-handoff.json").read_text(encoding="utf-8"))
    release_draft_handoff = json.loads((issues_dir / "release-draft-handoff.json").read_text(encoding="utf-8"))
    script = (issues_dir / "create-issues.sh").read_text(encoding="utf-8")
    readme = (issues_dir / "README.md").read_text(encoding="utf-8")

    assert "## Scope: promote candidate case `pypi-project-search`" in body
    assert "## Reproduction Context" in body
    assert "- Target URL: https://pypi.org/search/?q=cliany-site" in body
    assert "- Candidate commands:\n  - `cliany-site explore" in body
    assert "- Offline validation commands:\n  - `python scripts/validate_cases.py --strict`" in body
    assert 'cliany-site explore "https://pypi.org" "search Python packages" --json' in body
    assert "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md" in body
    assert metadata[0]["case_id"] == "pypi-project-search"
    assert metadata[0]["issue_title"] == "Promote candidate case `pypi-project-search` toward active"
    assert metadata[0]["issue_labels"] == ["case-proposal", "good first issue"]
    assert metadata[0]["target_url"] == "https://pypi.org/search/?q=cliany-site"
    assert metadata[0]["commands"] == [
        'cliany-site explore "https://pypi.org" "search Python packages" --json',
        "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json",
    ]
    assert metadata[0]["offline_commands"] == [
        "python scripts/validate_cases.py --strict",
        "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md",
    ]
    assert metadata[0]["issue_body_name"] == "pypi-project-search.md"
    assert metadata[0]["issue_body_file"].endswith("pypi-project-search.md")
    assert "gh issue create" in metadata[0]["create_command"]
    assert "--label case-proposal" in metadata[0]["create_command"]
    assert "--label 'good first issue'" in metadata[0]["create_command"]
    assert publication_handoff == {
        "publication_ok": False,
        "visibility": {
            "status": "dirty_worktree",
            "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
        },
        "next_actions": plan.next_actions,
        "publication_next_actions": [
            "Commit, stash, or discard local worktree changes before publishing release refs.",
            "Push `master` to `origin`; local branch is ahead by `2` commits.",
            "Push tag `v0.16.1` after the branch is published.",
        ],
        "ref_context": {
            "repo_root": "/repo/cliany.site",
            "branch": "master",
            "upstream": "origin/master",
            "remote": "origin",
            "local_head": "abc123",
            "upstream_head": "def456",
            "ahead_count": 2,
            "behind_count": 0,
            "latest_tag": "v0.16.1",
            "tag_commit": "abc123",
            "remote_checked": False,
        },
        "worktree_clean": False,
        "worktree_status": [" M CHANGELOG.md"],
        "publish_commands": ["python scripts/check_release_publication.py --json"],
        "publish_script_command": (
            "python scripts/check_release_publication.py --json "
            "--publish-script /tmp/cliany-publish-release.sh"
        ),
    }
    assert release_draft_handoff == {
        "release_draft_path": "docs/releases/v0.16.2-draft.md",
        "release_draft_issues": [
            "release draft is missing",
            "release draft missing snippet: ## 发版前验证",
        ],
        "target_version": "0.16.2",
    }
    assert "gh issue create" in script
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in script
    assert 'cd "$REPO_ROOT"' in script
    assert 'PREFLIGHT_JSON="/tmp/cliany-issue-publication-check.json"' in script
    assert (
        'if ! python scripts/check_release_publication.py --strict --json >"$PREFLIGHT_JSON"; then'
    ) in script
    assert "Release publication preflight failed; review $PREFLIGHT_JSON" in script
    assert 'cat "$PREFLIGHT_JSON" >&2' in script
    assert "  exit 1" in script
    assert "--body-file" in script
    assert "pypi-project-search.md" in script
    assert oct((issues_dir / "create-issues.sh").stat().st_mode & 0o777) == "0o755"
    assert "# cliany-site Candidate Issue Artifacts" in readme
    assert "Generated for target version `0.16.2`." in readme
    assert "`issue-metadata.json`: structured issue title, labels, reproduction context" in readme
    assert "body file name" in readme
    assert "`publication-handoff.json`: publication status, visibility, next actions" in readme
    assert "`release-draft-handoff.json`: target version, release draft path" in readme
    assert "## Candidate Summary" in readme
    assert "| Case | Issue Body | Target URL | Candidate Commands | Offline Validation Commands |" in readme
    assert (
        "| `pypi-project-search` | `pypi-project-search.md` | "
        "https://pypi.org/search/?q=cliany-site | 2 | 2 |"
    ) in readme
    assert "## Publication Handoff" in readme
    assert "publication_ok: `false`" in readme
    assert "visibility: `dirty_worktree`" in readme
    assert (
        "visibility_summary: Worktree has uncommitted changes; "
        "resolve them before publishing release refs."
    ) in readme
    assert "latest_tag: `v0.16.1`" in readme
    assert "local_head: `abc123`" in readme
    assert "worktree_clean: `false`" in readme
    assert "### Publication Next Actions" in readme
    assert "Commit, stash, or discard local worktree changes" in readme
    assert "Push `master` to `origin`; local branch is ahead by `2` commits." in readme
    assert "Push tag `v0.16.1` after the branch is published." in readme
    assert "### Publication Publish Script" in readme
    assert (
        "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    ) in readme
    assert "python scripts/check_release_publication.py --json" in readme
    assert "## Release Draft Handoff" in readme
    assert "release_draft_path: `docs/releases/v0.16.2-draft.md`" in readme
    assert "- release draft is missing" in readme
    assert "- release draft missing snippet: ## 发版前验证" in readme
    assert "Confirm release draft issues are resolved or intentionally deferred" in readme
    assert "Confirm `Publication Next Actions` are resolved or intentionally deferred" in readme
    assert "before running `create-issues.sh`" in readme
    assert "expected target URL, candidate commands" in readme
    assert "offline validation commands for each case" in readme
    assert "release publication preflight" in readme
    assert "python scripts/check_release_publication.py --strict --json" in readme
    assert "/tmp/cliany-issue-publication-check.json" in readme
    assert "prints that JSON before exiting" in readme
    assert "`create-issues.sh` is generated for review. It is not executed" in readme
    assert (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--issues-dir /tmp/cliany-candidate-issues"
    ) in readme
    assert "python scripts/validate_cases.py --strict" in readme


def test_plan_cli_writes_json_for_current_repo(capsys):
    exit_code = plan_next_iteration.main(["--json", "--target-version", "0.16.2"])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["target_version"] == "0.16.2"
    assert "recommended_theme" in payload
    assert "next_actions" in payload
