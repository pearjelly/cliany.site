import hashlib
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


def _stable_json_sha256(value: object) -> str:
    digest_source = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(digest_source).hexdigest()


def _write_pyproject(root: Path, version: str = "0.16.1") -> None:
    (root / "pyproject.toml").write_text(
        f"""
[project]
name = "cliany-site"
version = "{version}"
""",
        encoding="utf-8",
    )


def _promotion_evidence(package_next_action: str, smoke_next_action: str) -> dict[str, dict[str, str | None]]:
    return {
        "adapter_package": {
            "status": "pending",
            "evidence": None,
            "next_action": package_next_action,
        },
        "metadata_validation": {
            "status": "pending",
            "evidence": None,
            "next_action": "Run validate_cases with --packages-dir.",
        },
        "online_smoke": {
            "status": "pending",
            "evidence": None,
            "next_action": smoke_next_action,
        },
    }


def _pypi_promotion_command_plan(*, explore_query: str = "search Python packages") -> list[dict[str, object]]:
    return [
        {
            "task": "adapter_package",
            "command": f'cliany-site explore "https://pypi.org" "{explore_query}" --json',
            "source": "commands.explore",
            "missing": False,
        },
        {
            "task": "metadata_validation",
            "command": (
                "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
                "--include-candidate-packages --strict"
            ),
            "source": "candidate_package_validation_command",
            "missing": False,
        },
        {
            "task": "online_smoke",
            "command": "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json",
            "source": "commands.adapter",
            "missing": False,
        },
    ]


def test_candidate_issue_body_checks_complete_tasks():
    issue_body = plan_next_iteration._candidate_issue_body(
        case_id="mixed-candidate",
        target_url="https://example.test/search",
        commands=["cliany-site example.test search --json"],
        offline_commands=["python scripts/validate_cases.py --strict"],
        promotion_command_plan=[
            {
                "task": "online_smoke",
                "command": "cliany-site example.test search --json",
                "source": "commands.adapter",
                "missing": False,
            }
        ],
        adapter_package="Build adapter package.",
        metadata_validation="Validate metadata.",
        online_smoke="Run online smoke.",
        promotion_evidence={
            "adapter_package": {
                "status": "complete",
                "evidence": "example.test-v1.cliany-adapter.tar.gz",
                "next_action": "",
            },
            "metadata_validation": {
                "status": "blocked",
                "evidence": "Waiting for package validation.",
                "next_action": "Run package validation.",
            },
            "online_smoke": {
                "status": "pending",
                "evidence": None,
                "next_action": "Run read-only smoke.",
            },
        },
    )

    assert "## Primary Evidence Task" in issue_body
    assert "- Task: `online_smoke`" in issue_body
    assert "- Status: `pending`" in issue_body
    assert "- Next action: Run read-only smoke." in issue_body
    assert "## Promotion Command Plan" in issue_body
    assert "- `online_smoke`: `cliany-site example.test search --json`" in issue_body
    assert "- [x] `adapter_package`: Build adapter package." in issue_body
    assert "- [ ] `metadata_validation`: Validate metadata." in issue_body
    assert "- [ ] `online_smoke`: Run online smoke." in issue_body


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
                    promotion_evidence=_promotion_evidence(
                        "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
                        "Run read-only PyPI search smoke.",
                    ),
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
                    promotion_evidence=_promotion_evidence(
                        "Generate www.npmjs.com-<version>.cliany-adapter.tar.gz.",
                        "Run read-only npm search smoke.",
                    ),
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
        tag_points_at_head=True,
        tag_commit_in_upstream=False,
        branch_published=False,
        tag_published=False,
        remote_branch_head=None,
        remote_tag_commit=None,
        remote_checked=False,
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


def _published_publication_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=True,
        repo_root="/repo/cliany.site",
        branch="master",
        upstream="origin/master",
        remote="origin",
        local_head="abc123",
        upstream_head="abc123",
        ahead_count=0,
        behind_count=0,
        latest_tag="v0.16.1",
        tag_commit="abc123",
        tag_points_at_head=True,
        tag_commit_in_upstream=True,
        branch_published=True,
        tag_published=True,
        remote_branch_head="abc123",
        remote_tag_commit="abc123",
        remote_checked=True,
        worktree_clean=True,
        worktree_status=[],
        next_actions=[],
        publish_commands=[],
    )


def _tag_mismatch_publication_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=False,
        repo_root="/repo/cliany.site",
        branch="master",
        upstream="origin/master",
        remote="origin",
        local_head="new123",
        upstream_head="old456",
        ahead_count=2,
        behind_count=0,
        latest_tag="v0.16.1",
        tag_commit="tag789",
        tag_points_at_head=False,
        tag_commit_in_upstream=False,
        branch_published=False,
        tag_published=False,
        remote_branch_head=None,
        remote_tag_commit=None,
        remote_checked=False,
        worktree_clean=True,
        worktree_status=[],
        next_actions=[
            "- Push `master` to `origin`; local branch is ahead by `2` commits.",
            "- Move to the `v0.16.1` commit or create a new release tag at HEAD before publishing.",
            "- Push tag `v0.16.1` after the branch is published, or rerun with `--remote` "
            "to verify the live remote tag.",
            "- Rerun with `--remote` when network access is available to verify live remote refs.",
        ],
        publish_commands=[
            "git push origin master",
            "python scripts/check_release_publication.py --remote --json",
        ],
    )


def _blocked_candidate_issue_gate() -> dict[str, object]:
    reason_codes = [
        "publication_not_published",
        "dirty_worktree",
        "release_draft_issues",
    ]
    required_actions = [
        "Commit, stash, or discard local worktree changes before publishing release refs.",
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
        "Push tag `v0.16.1` after the branch is published.",
        "Resolve release draft issue: release draft is missing",
        "Resolve release draft issue: release draft missing snippet: ## 发版前验证",
    ]
    return {
        "status": "blocked_by_publication",
        "can_create_issues": False,
        "requires_maintainer_review": True,
        "summary": "Do not create candidate issues until the latest local release is publicly visible.",
        "reason_code_count": len(reason_codes),
        "reason_codes_sha256": _stable_json_sha256(reason_codes),
        "reason_codes": reason_codes,
        "primary_reason_code": "publication_not_published",
        "reason_descriptions": {
            "publication_not_published": "The latest local release branch or tag is not visible upstream.",
            "dirty_worktree": "The working tree has uncommitted changes that must be resolved first.",
            "release_draft_issues": "The target release draft still has validation issues.",
        },
        "primary_reason_description": "The latest local release branch or tag is not visible upstream.",
        "required_action_count": len(required_actions),
        "required_actions_sha256": _stable_json_sha256(required_actions),
        "required_actions": required_actions,
        "primary_required_action": (
            "Commit, stash, or discard local worktree changes before publishing release refs."
        ),
        "evidence": {
            "publication_ok": False,
            "publication_visibility_status": "dirty_worktree",
            "publication_worktree_clean": False,
            "publication_remote_checked": False,
            "publication_branch": "master",
            "publication_latest_tag": "v0.16.1",
            "publication_ahead_count": 2,
            "publication_tag_decision_status": "blocked_by_worktree",
            "publication_tag_can_push": False,
            "publication_tag_required_action": (
                "Commit, stash, or discard local worktree changes before publishing release refs."
            ),
            "release_draft_ok": False,
            "release_draft_path": "docs/releases/v0.16.2-draft.md",
            "release_draft_issue_count": 2,
        },
    }


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
    assert plan.case_promotion_evidence_summary["candidate_count"] == 2
    assert plan.case_promotion_evidence_summary["pending_count"] == 6
    assert plan.candidate_promotions[0].case_id == "pypi-project-search"


def test_plan_surfaces_tag_mismatch_before_publication(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_tag_mismatch_publication_report(),
    )

    assert plan.publication_visibility == {
        "status": "local_only",
        "summary": (
            "`master` is ahead of `origin` by 2 commits; `v0.16.1` does not point at HEAD, "
            "so publish `master` first and choose whether to move to that tag commit or create "
            "a new release tag at HEAD before publishing a tag."
        ),
    }
    assert plan.publication_publish_commands == [
        "git push origin master",
        "python scripts/check_release_publication.py --remote --json",
    ]
    assert plan.next_actions[:4] == [
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
        "Move to the `v0.16.1` commit or create a new release tag at HEAD before publishing.",
        "Push tag `v0.16.1` after the branch is published, or rerun with `--remote` to verify the live "
        "remote tag.",
        "Rerun with `--remote` when network access is available to verify live remote refs.",
    ]
    assert not any("push `master` and tag `v0.16.1`" in action for action in plan.next_actions)


def test_candidate_issue_gate_allows_creation_after_publication_with_release_draft_review(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    reason_codes = ["release_draft_issues"]
    required_actions = [
        "Resolve release draft issue: release draft is missing",
        "Resolve release draft issue: release draft missing snippet: ## 发版前验证",
    ]

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_published_publication_report(),
    )

    assert plan.candidate_issue_gate == {
        "status": "review_required",
        "can_create_issues": True,
        "requires_maintainer_review": True,
        "summary": "Release draft issues must be resolved or intentionally deferred before tagging.",
        "reason_code_count": len(reason_codes),
        "reason_codes_sha256": _stable_json_sha256(reason_codes),
        "reason_codes": reason_codes,
        "primary_reason_code": "release_draft_issues",
        "reason_descriptions": {
            "release_draft_issues": "The target release draft still has validation issues.",
        },
        "primary_reason_description": "The target release draft still has validation issues.",
        "required_action_count": len(required_actions),
        "required_actions_sha256": _stable_json_sha256(required_actions),
        "required_actions": required_actions,
        "primary_required_action": "Resolve release draft issue: release draft is missing",
        "evidence": {
            "publication_ok": True,
            "publication_visibility_status": "published",
            "publication_worktree_clean": True,
            "publication_remote_checked": True,
            "publication_branch": "master",
            "publication_latest_tag": "v0.16.1",
            "publication_ahead_count": 0,
            "publication_tag_decision_status": "published",
            "publication_tag_can_push": False,
            "publication_tag_required_action": None,
            "release_draft_ok": False,
            "release_draft_path": "docs/releases/v0.16.2-draft.md",
            "release_draft_issue_count": 2,
        },
    }


def test_summary_inline_code_uses_wider_fence_for_backticks():
    assert plan_next_iteration._summary_inline_code("Push `master` to `origin`") == (
        "`` Push `master` to `origin` ``"
    )
    assert plan_next_iteration._summary_inline_code("`master` is ahead") == (
        "`` `master` is ahead ``"
    )


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
    assert data["plan_report_command"] == (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--report /tmp/cliany-next-iteration.md"
    )
    assert data["commit_cadence"] == {
        "status": "needs_more_commit_days",
        "commit_days": [],
        "commit_day_count": 2,
        "min_commit_days": 3,
        "missing_commit_days": 1,
        "next_actions": ["Ship verified slices on `1` more unique commit days this week."],
        "summary": "2/3 commit days; 1 more unique day(s) needed.",
    }
    assert data["candidate_issue_gate"] == _blocked_candidate_issue_gate()
    assert not str(data["candidate_issue_gate"]["evidence"]["release_draft_path"]).startswith("/")
    assert data["publication_publish_commands"] == [
        "python scripts/check_release_publication.py --json",
    ]
    assert data["publication_publish_command_count"] == 1
    assert data["publication_publish_commands_sha256"] == _stable_json_sha256(
        data["publication_publish_commands"]
    )
    assert data["publication_primary_publish_command"] == data["publication_publish_commands"][0]
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
        "tag_points_at_head": True,
        "tag_commit_in_upstream": False,
        "branch_published": False,
        "tag_published": False,
        "remote_branch_head": None,
        "remote_tag_commit": None,
        "remote_checked": False,
    }
    assert data["publication_worktree_clean"] is False
    assert data["publication_worktree_status"] == [" M CHANGELOG.md"]
    assert (
        data["publication_publish_script_command"]
        == "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    )
    assert data["publication_publish_script_path"] == "/tmp/cliany-publish-release.sh"
    assert data["publication_publish_script_path_sha256"] == _stable_json_sha256(
        "/tmp/cliany-publish-release.sh"
    )
    assert data["publication_publish_script_command_sha256"] == _stable_json_sha256(
        "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    )
    assert data["publication_next_actions"] == [
        "Commit, stash, or discard local worktree changes before publishing release refs.",
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
        "Push tag `v0.16.1` after the branch is published.",
    ]
    assert data["publication_next_action_count"] == 3
    assert data["publication_next_actions_sha256"] == _stable_json_sha256(
        data["publication_next_actions"]
    )
    assert data["publication_primary_next_action"] == data["publication_next_actions"][0]
    assert data["next_action_count"] == len(data["next_actions"])
    assert data["next_actions_sha256"] == _stable_json_sha256(data["next_actions"])
    assert data["primary_next_action"] == data["next_actions"][0]
    assert any("Push `master`" in action for action in data["next_actions"])
    assert data["case_promotion_evidence_summary"]["candidate_count"] == 2
    assert data["case_promotion_evidence_summary"]["task_count"] == 6
    assert data["case_promotion_evidence_summary"]["status_counts"] == {
        "blocked": 0,
        "complete": 0,
        "pending": 6,
    }
    assert data["case_promotion_evidence_summary"]["primary_task"] == {
        "case_id": "pypi-project-search",
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
    }
    assert (
        data["case_promotion_evidence_summary"]["primary_task_detail"]
        == data["case_promotion_evidence_summary"]["primary_task"]
    )
    assert (
        data["case_promotion_evidence_summary"]["primary_next_task"]
        == data["case_promotion_evidence_summary"]["primary_task_detail"]
    )
    assert (
        data["case_promotion_evidence_primary_next_task"]
        == data["case_promotion_evidence_summary"]["primary_next_task"]
    )
    assert (
        data["case_promotion_evidence_primary_next_action"]
        == data["case_promotion_evidence_summary"]["primary_next_action"]
    )
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
        "promotion_evidence": _promotion_evidence(
            "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
            "Run read-only PyPI search smoke.",
        ),
        "promotion_evidence_primary_task": {
            "task": "adapter_package",
            "status": "pending",
            "evidence": "",
            "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        },
        "evidence_bundle_primary_next_task": {
            "task": "adapter_package",
            "status": "pending",
            "evidence": "",
            "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        },
        "candidate_package_validation_command": (
            "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
            "--include-candidate-packages --strict"
        ),
        "promotion_command_plan": _pypi_promotion_command_plan(),
        "evidence_bundle_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle"
        ),
        "evidence_bundle_json_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle --json"
        ),
        "issue_body": (
            "## Scope: promote candidate case `pypi-project-search`\n\n"
            "Move this candidate case one step closer to `active` without changing its status early.\n\n"
            "## Primary Evidence Task\n"
            "- Task: `adapter_package`\n"
            "- Status: `pending`\n"
            "- Current evidence: Not attached yet.\n"
            "- Next action: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n\n"
            "## Reproduction Context\n"
            "- Target URL: https://pypi.org/search/?q=cliany-site\n"
            "- Candidate commands:\n"
            '  - `cliany-site explore "https://pypi.org" "search Python packages" --json`\n'
            "  - `cliany-site pypi.org search-projects --query cliany-site --limit 5 --json`\n"
            "- Offline validation commands:\n"
            "  - `python scripts/validate_cases.py --strict`\n"
            "  - `python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md`\n\n"
            "## Promotion Command Plan\n"
            '- `adapter_package`: `cliany-site explore "https://pypi.org" "search Python packages" --json`\n'
            "- `metadata_validation`: `python scripts/validate_cases.py "
            "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`\n"
            "- `online_smoke`: `cliany-site pypi.org search-projects --query cliany-site "
            "--limit 5 --json`\n\n"
            "## Tasks\n"
            "- [ ] `adapter_package`: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "  - Current status: `pending`\n"
            "  - Current evidence: Not attached yet.\n"
            "  - Next action: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "- [ ] `metadata_validation`: Run validate_cases with --packages-dir.\n"
            "  - Current status: `pending`\n"
            "  - Current evidence: Not attached yet.\n"
            "  - Next action: Run validate_cases with --packages-dir.\n"
            "- [ ] `online_smoke`: Run read-only PyPI search smoke.\n"
            "  - Current status: `pending`\n"
            "  - Current evidence: Not attached yet.\n"
            "  - Next action: Run read-only PyPI search smoke.\n\n"
            "## Evidence Bundle\n"
            "- Human: `cliany-site cases --case-id pypi-project-search --evidence-bundle`\n"
            "- JSON: `cliany-site cases --case-id pypi-project-search --evidence-bundle --json`\n"
            "- Attach or paste the JSON output in the issue once evidence changes.\n\n"
            "## Validation Evidence\n"
            "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.\n"
            "- Candidate package validation command: `python scripts/validate_cases.py "
            "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`\n"
            "- Paste the local `scripts/validate_cases.py --packages-dir` result.\n"
            "- Paste the read-only JSON envelope summary with `data.quality.ok=true` and `row_count>0`.\n\n"
            "## Non-goals\n"
            "- Do not mark the case `active` until all three promotion tasks are complete.\n"
            "- Do not require real LLM keys or write runtime state into the repository."
        ),
    }


def test_plan_validation_commands_keep_package_gate_args(tmp_path):
    _write_pyproject(tmp_path)
    packages_dir = tmp_path / "packages dir"
    package_args = f"--packages-dir {plan_next_iteration.shlex.quote(str(packages_dir))} --require-packages"

    plan = plan_next_iteration.build_plan(
        tmp_path,
        packages_dir=packages_dir,
        require_packages=True,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )
    data = plan.to_dict()

    assert (
        data["validation_commands"][0]
        == f"python scripts/plan_next_iteration.py --target-version 0.16.2 {package_args} --json"
    )
    assert (
        data["validation_commands"][1]
        == f"python scripts/release_readiness.py --target-version 0.16.2 {package_args} --json"
    )
    assert data["validation_commands"][4] == (
        "python scripts/validate_cases.py "
        f"--packages-dir {plan_next_iteration.shlex.quote(str(packages_dir))} "
        "--include-candidate-packages --strict"
    )
    assert data["issue_artifacts_command"] == (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        f"{package_args} --issues-dir /tmp/cliany-candidate-issues"
    )
    assert data["plan_report_command"] == (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        f"{package_args} --report /tmp/cliany-next-iteration.md"
    )


def test_plan_passes_package_gate_args_to_readiness(tmp_path, monkeypatch):
    _write_pyproject(tmp_path)
    packages_dir = tmp_path / "packages"
    captured: dict[str, object] = {}

    def fake_build_readiness_report(root: Path, **kwargs: object):
        captured["root"] = root
        captured.update(kwargs)
        return _readiness_report()

    monkeypatch.setattr(plan_next_iteration, "build_readiness_report", fake_build_readiness_report)

    plan_next_iteration.build_plan(
        tmp_path,
        target_version="0.16.2",
        packages_dir=packages_dir,
        require_packages=True,
        publication_report=_publication_report(),
    )

    assert captured["root"] == tmp_path
    assert captured["packages_dir"] == packages_dir
    assert captured["require_packages"] is True


def test_plan_next_actions_skip_release_draft_when_draft_is_valid(tmp_path):
    _write_pyproject(tmp_path)
    readiness = _readiness_report()
    readiness.draft = SimpleNamespace(
        ok=True,
        path="/tmp/project/docs/releases/v0.16.2-draft.md",
        target_version="0.16.2",
        issues=[],
    )
    readiness.blockers = ["commit days 2/3"]

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_publication_report(),
    )

    assert plan.release_draft_issues == []
    assert not any("Draft and verify" in action for action in plan.next_actions)
    assert any("Push `master`" in action for action in plan.next_actions)
    assert any("more unique commit days" in action for action in plan.next_actions)
    assert any("Promote one candidate case" in action for action in plan.next_actions)


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
    assert "Evidence Bundle Primary Next Task" in text
    assert (
        "| `pypi-project-search` | Promote candidate case `pypi-project-search` toward active | "
        "`case-proposal`, `good first issue` | `adapter_package` |"
    ) in text
    assert "`case-proposal`, `good first issue`" in text
    assert "## Candidate Promotion Tasks" in text
    assert "## Candidate Promotion Evidence Summary" in text
    assert "| candidate_count | `2` |" in text
    assert "| pending_count | `6` |" in text
    assert "| primary_next_action | `Generate pypi.org-<version>.cliany-adapter.tar.gz.` |" in text
    assert "| case_promotion_evidence_primary_next_task | `{\"case_id\": \"pypi-project-search\"" in text
    assert "\"task\": \"adapter_package\"" in text
    assert (
        "| case_promotion_evidence_primary_next_action | "
        "`Generate pypi.org-<version>.cliany-adapter.tar.gz.` |"
        in text
    )
    assert (
        "| plan_report_command | "
        "`python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--report /tmp/cliany-next-iteration.md` |"
        in text
    )
    assert "| `pypi-project-search` | `adapter_package` | `pending` | - |" in text
    assert "| Case | Adapter Package | Metadata Validation | Online Smoke | Promotion Evidence |" in text
    assert "adapter_package: pending; next: Generate pypi.org-<version>.cliany-adapter.tar.gz." in text
    assert "## Candidate Issue Body Templates" in text
    assert "## Primary Evidence Task" in text
    assert "- Task: `adapter_package`" in text
    assert "  - Current status: `pending`" in text
    assert "  - Current evidence: Not attached yet." in text
    assert "## Evidence Bundle" in text
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in text
    assert "## Publication Publish Commands" in text
    assert "| publication_next_action_count | `3` |" in text
    assert (
        "| publication_next_actions_sha256 | "
        f"`{_stable_json_sha256(plan.publication_next_actions)}` |"
    ) in text
    assert (
        "| publication_primary_next_action | "
        "`Commit, stash, or discard local worktree changes before publishing release refs.` |"
    ) in text
    assert "| publication_publish_command_count | `1` |" in text
    assert (
        "| publication_publish_commands_sha256 | "
        f"`{_stable_json_sha256(plan.publication_publish_commands)}` |"
    ) in text
    assert (
        "| publication_primary_publish_command | "
        "`python scripts/check_release_publication.py --json` |"
    ) in text
    assert f"| next_action_count | `{len(plan.next_actions)}` |" in text
    assert f"| next_actions_sha256 | `{_stable_json_sha256(plan.next_actions)}` |" in text
    assert (
        "| primary_next_action | "
        "`Commit, stash, or discard local worktree changes before publishing release refs.` |"
        in text
    )
    assert "| commit_cadence_status | `needs_more_commit_days` |" in text
    assert "| commit_cadence_missing_commit_days | `1` |" in text
    assert "| commit_cadence_summary | 2/3 commit days; 1 more unique day(s) needed. |" in text
    assert "## Candidate Issue Gate" in text
    assert "status: `blocked_by_publication`" in text
    assert "can_create_issues: `false`" in text
    assert "requires_maintainer_review: `true`" in text
    assert "Do not create candidate issues until the latest local release is publicly visible." in text
    assert "reason_code_count: `3`" in text
    assert f"reason_codes_sha256: `{_blocked_candidate_issue_gate()['reason_codes_sha256']}`" in text
    assert "required_action_count: `5`" in text
    assert f"required_actions_sha256: `{_blocked_candidate_issue_gate()['required_actions_sha256']}`" in text
    assert "### Candidate Issue Gate Reason Codes" in text
    assert "- `publication_not_published`" in text
    assert "- `dirty_worktree`" in text
    assert "- `release_draft_issues`" in text
    assert "### Candidate Issue Gate Reason Descriptions" in text
    assert "| `publication_not_published` | The latest local release branch or tag is not visible upstream. |" in text
    assert "| `dirty_worktree` | The working tree has uncommitted changes that must be resolved first. |" in text
    assert "| `release_draft_issues` | The target release draft still has validation issues. |" in text
    assert "### Candidate Issue Gate Evidence" in text
    assert "| publication_visibility_status | `dirty_worktree` |" in text
    assert "| publication_worktree_clean | `false` |" in text
    assert "| publication_latest_tag | `v0.16.1` |" in text
    assert "| publication_ahead_count | `2` |" in text
    assert "| release_draft_ok | `false` |" in text
    assert "| release_draft_issue_count | `2` |" in text
    assert "### Candidate Issue Gate Actions" in text
    assert "Resolve release draft issue: release draft is missing" in text
    assert "Resolve release draft issue: release draft missing snippet: ## 发版前验证" in text
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
    publish_script_command = (
        "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    )
    assert "| publication_publish_script_path | `/tmp/cliany-publish-release.sh` |" in text
    assert (
        "| publication_publish_script_path_sha256 | "
        f"`{_stable_json_sha256('/tmp/cliany-publish-release.sh')}` |"
    ) in text
    assert (
        "| publication_publish_script_command_sha256 | "
        f"`{_stable_json_sha256(publish_script_command)}` |"
    ) in text
    assert "- path: `/tmp/cliany-publish-release.sh`" in text
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


def test_plan_text_output_expands_candidate_issue_gate_evidence(tmp_path, capsys):
    _write_pyproject(tmp_path)
    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_publication_report(),
    )

    plan_next_iteration._print_text(plan)

    text = capsys.readouterr().out
    assert "commit_cadence:" in text
    assert (
        "plan_report_command: python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--report /tmp/cliany-next-iteration.md"
        in text
    )
    assert "- status: needs_more_commit_days" in text
    assert "- missing_commit_days: 1" in text
    assert "case_promotion_evidence_primary_next_task:" in text
    assert "  case_id: pypi-project-search" in text
    assert "  task: adapter_package" in text
    assert (
        "case_promotion_evidence_primary_next_action: "
        "Generate pypi.org-<version>.cliany-adapter.tar.gz."
        in text
    )
    assert "candidate_promotions:" in text
    assert "  evidence_bundle_primary_next_task:" in text
    assert "    task: adapter_package" in text
    assert "candidate_issue_gate:" in text
    assert "publication_next_action_count: 3" in text
    assert f"publication_next_actions_sha256: {_stable_json_sha256(plan.publication_next_actions)}" in text
    assert (
        "publication_primary_next_action: "
        "Commit, stash, or discard local worktree changes before publishing release refs."
        in text
    )
    assert f"next_action_count: {len(plan.next_actions)}" in text
    assert f"next_actions_sha256: {_stable_json_sha256(plan.next_actions)}" in text
    assert (
        "primary_next_action: "
        "Commit, stash, or discard local worktree changes before publishing release refs."
        in text
    )
    assert "publication_publish_command_count: 1" in text
    assert (
        f"publication_publish_commands_sha256: "
        f"{_stable_json_sha256(plan.publication_publish_commands)}"
        in text
    )
    assert "publication_primary_publish_command: python scripts/check_release_publication.py --json" in text
    assert "- reason_code_count: 3" in text
    assert f"- reason_codes_sha256: {_blocked_candidate_issue_gate()['reason_codes_sha256']}" in text
    assert "- required_action_count: 5" in text
    assert f"- required_actions_sha256: {_blocked_candidate_issue_gate()['required_actions_sha256']}" in text
    assert "- reason_codes:" in text
    assert "  - publication_not_published" in text
    assert "  - dirty_worktree" in text
    assert "  - release_draft_issues" in text
    assert "- reason_descriptions:" in text
    assert "  - publication_not_published: The latest local release branch or tag is not visible upstream." in text
    assert "  - dirty_worktree: The working tree has uncommitted changes that must be resolved first." in text
    assert "  - release_draft_issues: The target release draft still has validation issues." in text
    assert "- evidence:" in text
    assert "  - publication_visibility_status: dirty_worktree" in text
    assert "  - publication_worktree_clean: false" in text
    assert "  - publication_latest_tag: v0.16.1" in text
    assert "  - publication_ahead_count: 2" in text
    assert "  - release_draft_ok: false" in text
    assert "  - release_draft_issue_count: 2" in text
    assert "'publication_visibility_status':" not in text


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
    artifact_manifest = json.loads((issues_dir / "artifact-manifest.json").read_text(encoding="utf-8"))
    metadata = json.loads((issues_dir / "issue-metadata.json").read_text(encoding="utf-8"))
    publication_handoff = json.loads((issues_dir / "publication-handoff.json").read_text(encoding="utf-8"))
    release_draft_handoff = json.loads((issues_dir / "release-draft-handoff.json").read_text(encoding="utf-8"))
    script = (issues_dir / "create-issues.sh").read_text(encoding="utf-8")
    readme = (issues_dir / "README.md").read_text(encoding="utf-8")
    issue_body_inventory = []
    for body_name in ("pypi-project-search.md", "npm-package-search.md"):
        body_bytes = (issues_dir / body_name).read_bytes()
        issue_body_inventory.append(
            {
                "case_id": body_name.removesuffix(".md"),
                "issue_body_name": body_name,
                "byte_count": len(body_bytes),
                "sha256": hashlib.sha256(body_bytes).hexdigest(),
            }
        )
    summary_bytes = json.dumps(
        issue_body_inventory,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    issue_body_summary = {
        "body_count": len(issue_body_inventory),
        "total_byte_count": sum(item["byte_count"] for item in issue_body_inventory),
        "inventory_sha256": hashlib.sha256(summary_bytes).hexdigest(),
    }
    issue_body_inventory_preview = issue_body_inventory[:8]
    issue_body_inventory_tail = issue_body_inventory[-8:]
    issue_body_inventory_boundary = {
        "first_entry": issue_body_inventory[0],
        "last_entry": issue_body_inventory[-1],
    }
    issue_body_summary_keys = list(issue_body_summary)
    issue_body_summary_key_boundary = {
        "first_key": issue_body_summary_keys[0],
        "last_key": issue_body_summary_keys[-1],
    }
    issue_body_summary_key_preview = issue_body_summary_keys[:8]
    issue_body_summary_key_tail = issue_body_summary_keys[-8:]
    stable_issue_metadata = [
        {
            "case_id": item["case_id"],
            "issue_title": item["issue_title"],
            "issue_labels": item["issue_labels"],
            "target_url": item["target_url"],
            "commands": item["commands"],
            "offline_commands": item["offline_commands"],
            "promotion_evidence": item["promotion_evidence"],
            "promotion_evidence_primary_task": item["promotion_evidence_primary_task"],
            "evidence_bundle_primary_next_task": item["evidence_bundle_primary_next_task"],
            "candidate_package_validation_command": item["candidate_package_validation_command"],
            "promotion_command_plan": item["promotion_command_plan"],
            "evidence_bundle_command": item["evidence_bundle_command"],
            "evidence_bundle_json_command": item["evidence_bundle_json_command"],
            "issue_body_name": item["issue_body_name"],
        }
        for item in metadata
    ]
    issue_metadata_boundary = {
        "first_item": stable_issue_metadata[0],
        "last_item": stable_issue_metadata[-1],
    }
    issue_metadata_preview = stable_issue_metadata[:8]
    issue_metadata_tail = stable_issue_metadata[-8:]
    issue_metadata_summary = {
        "metadata_count": len(stable_issue_metadata),
        "metadata_sha256": _stable_json_sha256(stable_issue_metadata),
        "metadata_first_item": issue_metadata_boundary["first_item"],
        "metadata_last_item": issue_metadata_boundary["last_item"],
        "metadata_boundary_sha256": _stable_json_sha256(
            issue_metadata_boundary
        ),
        "metadata_preview_count": len(issue_metadata_preview),
        "metadata_preview": list(issue_metadata_preview),
        "metadata_preview_sha256": _stable_json_sha256(issue_metadata_preview),
        "metadata_tail_count": len(issue_metadata_tail),
        "metadata_tail": list(issue_metadata_tail),
        "metadata_tail_sha256": _stable_json_sha256(issue_metadata_tail),
    }
    expected_release_draft_handoff = {
        "schema_version": 1,
        "release_draft_ok": False,
        "release_draft_issue_count": 2,
        "release_draft_path": "docs/releases/v0.16.2-draft.md",
        "release_draft_path_sha256": _stable_json_sha256("docs/releases/v0.16.2-draft.md"),
        "release_draft_primary_issue": "release draft is missing",
        "primary_issue": "release draft is missing",
        "release_draft_primary_required_action": "Resolve release draft issue: release draft is missing",
        "primary_required_action": "Resolve release draft issue: release draft is missing",
        "release_draft_required_action_count": 2,
        "release_draft_required_actions_sha256": _stable_json_sha256(
            [
                "Resolve release draft issue: release draft is missing",
                "Resolve release draft issue: release draft missing snippet: ## 发版前验证",
            ]
        ),
        "release_draft_required_actions": [
            "Resolve release draft issue: release draft is missing",
            "Resolve release draft issue: release draft missing snippet: ## 发版前验证",
        ],
        "release_draft_issues_sha256": _stable_json_sha256(
            [
                "release draft is missing",
                "release draft missing snippet: ## 发版前验证",
            ]
        ),
        "release_draft_issues": [
            "release draft is missing",
            "release draft missing snippet: ## 发版前验证",
        ],
        "plan_report_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--report /tmp/cliany-next-iteration.md"
        ),
        "plan_report_command_sha256": _stable_json_sha256(
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--report /tmp/cliany-next-iteration.md"
        ),
        "issue_artifacts_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
        "issue_artifacts_command_sha256": _stable_json_sha256(
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
        "target_version": "0.16.2",
    }
    release_draft_handoff_keys = list(expected_release_draft_handoff)
    release_draft_handoff_key_preview = release_draft_handoff_keys[:8]
    release_draft_handoff_key_tail = release_draft_handoff_keys[-8:]
    expected_tag_publish_decision = {
        "status": "blocked_by_worktree",
        "can_push_tag": False,
        "latest_tag": "v0.16.1",
        "tag_points_at_head": True,
        "tag_published": False,
        "required_action": (
            "Commit, stash, or discard local worktree changes before publishing release refs."
        ),
    }
    expected_publication_handoff = {
        "schema_version": 1,
        "publication_ok": False,
        "candidate_issue_gate": _blocked_candidate_issue_gate(),
        "candidate_issue_gate_primary_reason_code": "publication_not_published",
        "candidate_issue_gate_primary_reason_description": (
            "The latest local release branch or tag is not visible upstream."
        ),
        "candidate_issue_gate_primary_required_action": (
            "Commit, stash, or discard local worktree changes before publishing release refs."
        ),
        "visibility": {
            "status": "dirty_worktree",
            "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
        },
        "tag_publish_decision": expected_tag_publish_decision,
        "next_actions": plan.next_actions,
        "commit_cadence": plan.commit_cadence,
        "commit_cadence_status": "needs_more_commit_days",
        "commit_cadence_missing_commit_days": 1,
        "commit_cadence_primary_next_action": (
            "Ship verified slices on `1` more unique commit days this week."
        ),
        "publication_next_actions": [
            "Commit, stash, or discard local worktree changes before publishing release refs.",
            "Push `master` to `origin`; local branch is ahead by `2` commits.",
            "Push tag `v0.16.1` after the branch is published.",
        ],
        "primary_next_action": "Commit, stash, or discard local worktree changes before publishing release refs.",
        "plan_report_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--report /tmp/cliany-next-iteration.md"
        ),
        "plan_report_command_sha256": _stable_json_sha256(
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--report /tmp/cliany-next-iteration.md"
        ),
        "issue_artifacts_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
        "issue_artifacts_command_sha256": _stable_json_sha256(
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
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
            "tag_points_at_head": True,
            "tag_commit_in_upstream": False,
            "branch_published": False,
            "tag_published": False,
            "remote_branch_head": None,
            "remote_tag_commit": None,
            "remote_checked": False,
        },
        "worktree_clean": False,
        "worktree_status": [" M CHANGELOG.md"],
        "publish_command_count": 1,
        "primary_publish_command": "python scripts/check_release_publication.py --json",
        "publish_commands": ["python scripts/check_release_publication.py --json"],
        "publish_script_path": "/tmp/cliany-publish-release.sh",
        "publish_script_path_sha256": _stable_json_sha256("/tmp/cliany-publish-release.sh"),
        "publish_script_command": (
            "python scripts/check_release_publication.py --json "
            "--publish-script /tmp/cliany-publish-release.sh"
        ),
        "publish_script_command_sha256": _stable_json_sha256(
            "python scripts/check_release_publication.py --json "
            "--publish-script /tmp/cliany-publish-release.sh"
        ),
    }
    publication_handoff_keys = list(expected_publication_handoff)
    publication_handoff_key_preview = publication_handoff_keys[:8]
    publication_handoff_key_tail = publication_handoff_keys[-8:]
    expected_artifact_files = {
        "readme": "README.md",
        "issue_metadata": "issue-metadata.json",
        "publication_handoff": "publication-handoff.json",
        "release_draft_handoff": "release-draft-handoff.json",
        "create_issues_script": "create-issues.sh",
        "issue_bodies": ["pypi-project-search.md", "npm-package-search.md"],
    }
    artifact_file_keys = list(expected_artifact_files)
    artifact_files_key_boundary = {
        "first_key": artifact_file_keys[0],
        "last_key": artifact_file_keys[-1],
    }
    artifact_files_key_preview = artifact_file_keys[:8]
    artifact_files_key_tail = artifact_file_keys[-8:]
    publication_visibility_keys = list(plan.publication_visibility)
    publication_visibility_key_boundary = {
        "first_key": publication_visibility_keys[0],
        "last_key": publication_visibility_keys[-1],
    }
    publication_visibility_key_preview = publication_visibility_keys[:8]
    publication_visibility_key_tail = publication_visibility_keys[-8:]
    tag_publish_decision_keys = list(expected_tag_publish_decision)
    tag_publish_decision_key_boundary = {
        "first_key": tag_publish_decision_keys[0],
        "last_key": tag_publish_decision_keys[-1],
    }
    tag_publish_decision_key_preview = tag_publish_decision_keys[:8]
    tag_publish_decision_key_tail = tag_publish_decision_keys[-8:]
    publication_ref_context_keys = list(plan.publication_ref_context)
    publication_ref_context_key_preview = publication_ref_context_keys[:8]
    publication_ref_context_key_tail = publication_ref_context_keys[-8:]
    blocker_boundary = {
        "first_item": plan.blockers[0] if plan.blockers else None,
        "last_item": plan.blockers[-1] if plan.blockers else None,
    }
    blocker_preview = plan.blockers[:8]
    blocker_tail = plan.blockers[-8:]
    next_action_boundary = {
        "first_item": plan.next_actions[0] if plan.next_actions else None,
        "last_item": plan.next_actions[-1] if plan.next_actions else None,
    }
    next_action_preview = plan.next_actions[:8]
    next_action_tail = plan.next_actions[-8:]
    publication_next_action_preview = plan.publication_next_actions[:8]
    publication_next_action_tail = plan.publication_next_actions[-8:]
    expected_validation_commands = [
        (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
        (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--report /tmp/cliany-next-iteration.md"
        ),
        "python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
        "python scripts/release_readiness.py --target-version 0.16.2 --json",
        "python scripts/check_release_publication.py --json",
        "python scripts/validate_cases.py --strict",
    ]
    expected_review_checklist = [
        "Confirm the latest local release has been published before creating new candidate work.",
        (
            "Confirm release draft issues are resolved or intentionally deferred before tagging the "
            "target version."
        ),
        (
            "Confirm Publication Next Actions are resolved or intentionally deferred before running "
            "create-issues.sh."
        ),
        (
            "Confirm issue-metadata.json has the expected target URL, candidate commands, "
            "offline validation commands, candidate_package_validation_command, "
            "and promotion_command_plan for each case."
        ),
        "Review each body file for scope, tasks, validation evidence, and non-goals.",
        (
            "Keep cases as candidate until adapter package, metadata validation, "
            "and online smoke evidence are complete."
        ),
        "Do not use real LLM keys or write runtime state into the repository.",
    ]
    expected_create_issues_safety_contract = {
        "dry_run_supported": True,
        "dry_run_env": "CLIANY_CREATE_ISSUES_DRY_RUN=1",
        "preflight_required": True,
        "preflight_command": "python scripts/check_release_publication.py --strict --json",
        "preflight_json": "/tmp/cliany-issue-publication-check.json",
    }
    create_issues_safety_contract_keys = list(expected_create_issues_safety_contract)
    review_order = [
        "README.md",
        "publication-handoff.json",
        "release-draft-handoff.json",
        "issue-metadata.json",
        "pypi-project-search.md",
        "npm-package-search.md",
        "create-issues.sh",
    ]
    review_order_bytes = json.dumps(
        review_order,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    review_order_sha256 = hashlib.sha256(review_order_bytes).hexdigest()
    review_order_boundary = {
        "first_item": review_order[0],
        "last_item": review_order[-1],
    }
    review_order_preview = review_order[:8]
    review_order_tail = review_order[-8:]
    candidate_issue_gate_evidence = _blocked_candidate_issue_gate()["evidence"]
    candidate_issue_gate_evidence_keys = list(candidate_issue_gate_evidence)
    candidate_issue_gate_evidence_key_boundary = {
        "first_key": candidate_issue_gate_evidence_keys[0],
        "last_key": candidate_issue_gate_evidence_keys[-1],
    }
    candidate_issue_gate_reason_descriptions = _blocked_candidate_issue_gate()["reason_descriptions"]
    case_promotion_evidence_summary_keys = list(plan.case_promotion_evidence_summary)
    case_promotion_evidence_summary_key_boundary = {
        "first_key": case_promotion_evidence_summary_keys[0],
        "last_key": case_promotion_evidence_summary_keys[-1],
    }
    case_promotion_evidence_summary_key_preview = case_promotion_evidence_summary_keys[:8]
    case_promotion_evidence_summary_key_tail = case_promotion_evidence_summary_keys[-8:]
    command_plan_summary = plan.case_promotion_command_plan_summary
    create_issues_safety = {
        "script": str(issues_dir / "create-issues.sh"),
        "dry_run_supported": True,
        "dry_run_env": "CLIANY_CREATE_ISSUES_DRY_RUN=1",
        "dry_run_command": f"CLIANY_CREATE_ISSUES_DRY_RUN=1 {issues_dir / 'create-issues.sh'}",
        "preflight_required": True,
        "preflight_command": "python scripts/check_release_publication.py --strict --json",
        "preflight_json": "/tmp/cliany-issue-publication-check.json",
    }
    artifact_manifest_payload = plan_next_iteration._artifact_manifest_payload_without_summary(
        plan=plan,
        candidate_cases=["pypi-project-search", "npm-package-search"],
        review_order=review_order,
        issue_body_inventory=issue_body_inventory,
        issue_body_summary=issue_body_summary,
        issue_metadata_summary=issue_metadata_summary,
        create_issues_safety=create_issues_safety,
        artifact_files=expected_artifact_files,
    )
    artifact_bundle_summary = {
        "artifact_bundle_summary_key_count": len(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS),
        "artifact_bundle_summary_keys_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS
        ),
        "artifact_bundle_summary_key_preview_count": len(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW
        ),
        "artifact_bundle_summary_key_preview": list(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW
        ),
        "artifact_bundle_summary_key_preview_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW
        ),
        "artifact_bundle_summary_key_tail_count": len(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL
        ),
        "artifact_bundle_summary_key_tail": list(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL
        ),
        "artifact_bundle_summary_key_tail_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL
        ),
        "artifact_bundle_summary_first_key": (
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY["first_key"]
        ),
        "artifact_bundle_summary_last_key": (
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY["last_key"]
        ),
        "artifact_bundle_summary_key_boundary_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY
        ),
        "artifact_manifest_schema_version": plan_next_iteration.ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "artifact_manifest_key_count": len(plan_next_iteration.ARTIFACT_MANIFEST_KEYS),
        "artifact_manifest_keys_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_KEYS
        ),
        "artifact_manifest_first_key": plan_next_iteration.ARTIFACT_MANIFEST_KEY_BOUNDARY[
            "first_key"
        ],
        "artifact_manifest_last_key": plan_next_iteration.ARTIFACT_MANIFEST_KEY_BOUNDARY[
            "last_key"
        ],
        "artifact_manifest_key_boundary_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_BOUNDARY
        ),
        "artifact_manifest_key_preview_count": len(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_PREVIEW
        ),
        "artifact_manifest_key_preview": list(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_PREVIEW
        ),
        "artifact_manifest_key_preview_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_PREVIEW
        ),
        "artifact_manifest_key_tail_count": len(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_TAIL
        ),
        "artifact_manifest_key_tail": list(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_TAIL
        ),
        "artifact_manifest_key_tail_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_KEY_TAIL
        ),
        "artifact_manifest_payload_key_count": len(artifact_manifest_payload),
        "artifact_manifest_payload_first_key": (
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY["first_key"]
        ),
        "artifact_manifest_payload_last_key": (
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY["last_key"]
        ),
        "artifact_manifest_payload_key_boundary_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY
        ),
        "artifact_manifest_payload_key_preview_count": len(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW
        ),
        "artifact_manifest_payload_key_preview": list(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW
        ),
        "artifact_manifest_payload_key_preview_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW
        ),
        "artifact_manifest_payload_key_tail_count": len(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL
        ),
        "artifact_manifest_payload_key_tail": list(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL
        ),
        "artifact_manifest_payload_key_tail_sha256": _stable_json_sha256(
            plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL
        ),
        "artifact_manifest_payload_sha256": _stable_json_sha256(artifact_manifest_payload),
        "target_version": "0.16.2",
        "candidate_count": 2,
        "candidate_cases_first_case": "pypi-project-search",
        "candidate_cases_last_case": "npm-package-search",
        "candidate_cases_boundary_sha256": _stable_json_sha256(
            {
                "first_case": "pypi-project-search",
                "last_case": "npm-package-search",
            }
        ),
        "candidate_cases_preview_count": 2,
        "candidate_cases_preview": ["pypi-project-search", "npm-package-search"],
        "candidate_cases_preview_sha256": _stable_json_sha256(
            ["pypi-project-search", "npm-package-search"]
        ),
        "candidate_cases_tail_count": 2,
        "candidate_cases_tail": ["pypi-project-search", "npm-package-search"],
        "candidate_cases_tail_sha256": _stable_json_sha256(
            ["pypi-project-search", "npm-package-search"]
        ),
        "candidate_cases_sha256": _stable_json_sha256(["pypi-project-search", "npm-package-search"]),
        "case_promotion_evidence_summary_key_count": len(plan.case_promotion_evidence_summary),
        "case_promotion_evidence_summary_keys_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_keys
        ),
        "case_promotion_evidence_summary_first_key": (
            case_promotion_evidence_summary_key_boundary["first_key"]
        ),
        "case_promotion_evidence_summary_last_key": (
            case_promotion_evidence_summary_key_boundary["last_key"]
        ),
        "case_promotion_evidence_summary_key_boundary_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_key_boundary
        ),
        "case_promotion_evidence_summary_key_preview_count": len(
            case_promotion_evidence_summary_key_preview
        ),
        "case_promotion_evidence_summary_key_preview": list(
            case_promotion_evidence_summary_key_preview
        ),
        "case_promotion_evidence_summary_key_preview_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_key_preview
        ),
        "case_promotion_evidence_summary_key_tail_count": len(
            case_promotion_evidence_summary_key_tail
        ),
        "case_promotion_evidence_summary_key_tail": list(
            case_promotion_evidence_summary_key_tail
        ),
        "case_promotion_evidence_summary_key_tail_sha256": _stable_json_sha256(
            case_promotion_evidence_summary_key_tail
        ),
        "case_promotion_evidence_summary_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary
        ),
        "case_promotion_evidence_candidate_count": 2,
        "case_promotion_evidence_task_count": 6,
        "case_promotion_evidence_pending_count": 6,
        "case_promotion_evidence_blocked_count": 0,
        "case_promotion_evidence_complete_count": 0,
        "case_promotion_evidence_primary_next_action": (
            "Generate pypi.org-<version>.cliany-adapter.tar.gz."
        ),
        "case_promotion_evidence_primary_case_id": "pypi-project-search",
        "case_promotion_evidence_primary_task": "adapter_package",
        "case_promotion_evidence_primary_status": "pending",
        "case_promotion_evidence_primary_evidence_sha256": _stable_json_sha256(""),
        "case_promotion_evidence_primary_detail_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary["primary_task_detail"]
        ),
        "case_promotion_evidence_primary_next_task_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary["primary_next_task"]
        ),
        "case_promotion_command_plan_summary_sha256": _stable_json_sha256(
            command_plan_summary
        ),
        "case_promotion_command_plan_candidate_count": command_plan_summary["candidate_count"],
        "case_promotion_command_plan_command_count": command_plan_summary["command_count"],
        "case_promotion_command_plan_missing_command_count": command_plan_summary[
            "missing_command_count"
        ],
        "case_promotion_command_plan_all_declared": command_plan_summary["all_declared"],
        "body_count": 2,
        "issue_body_inventory_preview_count": len(issue_body_inventory_preview),
        "issue_body_inventory_preview": list(issue_body_inventory_preview),
        "issue_body_inventory_preview_sha256": _stable_json_sha256(
            issue_body_inventory_preview
        ),
        "issue_body_inventory_first_entry": issue_body_inventory_boundary[
            "first_entry"
        ],
        "issue_body_inventory_last_entry": issue_body_inventory_boundary["last_entry"],
        "issue_body_inventory_boundary_sha256": _stable_json_sha256(
            issue_body_inventory_boundary
        ),
        "issue_body_inventory_tail_count": len(issue_body_inventory_tail),
        "issue_body_inventory_tail": list(issue_body_inventory_tail),
        "issue_body_inventory_tail_sha256": _stable_json_sha256(
            issue_body_inventory_tail
        ),
        "issue_body_summary_key_count": len(issue_body_summary),
        "issue_body_summary_keys_sha256": _stable_json_sha256(
            issue_body_summary_keys
        ),
        "issue_body_summary_first_key": issue_body_summary_key_boundary[
            "first_key"
        ],
        "issue_body_summary_last_key": issue_body_summary_key_boundary["last_key"],
        "issue_body_summary_key_boundary_sha256": _stable_json_sha256(
            issue_body_summary_key_boundary
        ),
        "issue_body_summary_key_preview_count": len(issue_body_summary_key_preview),
        "issue_body_summary_key_preview": list(issue_body_summary_key_preview),
        "issue_body_summary_key_preview_sha256": _stable_json_sha256(
            issue_body_summary_key_preview
        ),
        "issue_body_summary_key_tail_count": len(issue_body_summary_key_tail),
        "issue_body_summary_key_tail": list(issue_body_summary_key_tail),
        "issue_body_summary_key_tail_sha256": _stable_json_sha256(
            issue_body_summary_key_tail
        ),
        "issue_body_summary_sha256": _stable_json_sha256(issue_body_summary),
        "review_item_count": len(review_order),
        "review_order_sha256": review_order_sha256,
        "review_order_first_item": review_order_boundary["first_item"],
        "review_order_last_item": review_order_boundary["last_item"],
        "review_order_boundary_sha256": _stable_json_sha256(
            review_order_boundary
        ),
        "review_order_preview_count": len(review_order_preview),
        "review_order_preview": list(review_order_preview),
        "review_order_preview_sha256": _stable_json_sha256(review_order_preview),
        "review_order_tail_count": len(review_order_tail),
        "review_order_tail": list(review_order_tail),
        "review_order_tail_sha256": _stable_json_sha256(review_order_tail),
        "inventory_sha256": issue_body_summary["inventory_sha256"],
        "issue_metadata_count": issue_metadata_summary["metadata_count"],
        "issue_metadata_sha256": issue_metadata_summary["metadata_sha256"],
        "issue_metadata_first_item": issue_metadata_summary[
            "metadata_first_item"
        ],
        "issue_metadata_last_item": issue_metadata_summary["metadata_last_item"],
        "issue_metadata_boundary_sha256": issue_metadata_summary[
            "metadata_boundary_sha256"
        ],
        "issue_metadata_preview_count": issue_metadata_summary[
            "metadata_preview_count"
        ],
        "issue_metadata_preview": list(issue_metadata_summary["metadata_preview"]),
        "issue_metadata_preview_sha256": issue_metadata_summary[
            "metadata_preview_sha256"
        ],
        "issue_metadata_tail_count": issue_metadata_summary[
            "metadata_tail_count"
        ],
        "issue_metadata_tail": list(issue_metadata_summary["metadata_tail"]),
        "issue_metadata_tail_sha256": issue_metadata_summary[
            "metadata_tail_sha256"
        ],
        "artifact_files_key_count": len(expected_artifact_files),
        "artifact_files_sha256": _stable_json_sha256(expected_artifact_files),
        "artifact_files_first_key": artifact_files_key_boundary["first_key"],
        "artifact_files_last_key": artifact_files_key_boundary["last_key"],
        "artifact_files_key_boundary_sha256": _stable_json_sha256(
            artifact_files_key_boundary
        ),
        "artifact_files_key_preview_count": len(artifact_files_key_preview),
        "artifact_files_key_preview": list(artifact_files_key_preview),
        "artifact_files_key_preview_sha256": _stable_json_sha256(
            artifact_files_key_preview
        ),
        "artifact_files_key_tail_count": len(artifact_files_key_tail),
        "artifact_files_key_tail": list(artifact_files_key_tail),
        "artifact_files_key_tail_sha256": _stable_json_sha256(
            artifact_files_key_tail
        ),
        "issue_artifacts_command_sha256": _stable_json_sha256(plan.issue_artifacts_command),
        "plan_report_command_sha256": _stable_json_sha256(plan.plan_report_command),
        "publication_visibility_key_count": len(plan.publication_visibility),
        "publication_visibility_sha256": _stable_json_sha256(plan.publication_visibility),
        "publication_visibility_first_key": publication_visibility_key_boundary[
            "first_key"
        ],
        "publication_visibility_last_key": publication_visibility_key_boundary[
            "last_key"
        ],
        "publication_visibility_key_boundary_sha256": _stable_json_sha256(
            publication_visibility_key_boundary
        ),
        "publication_visibility_key_preview_count": len(
            publication_visibility_key_preview
        ),
        "publication_visibility_key_preview": list(publication_visibility_key_preview),
        "publication_visibility_key_preview_sha256": _stable_json_sha256(
            publication_visibility_key_preview
        ),
        "publication_visibility_key_tail_count": len(
            publication_visibility_key_tail
        ),
        "publication_visibility_key_tail": list(publication_visibility_key_tail),
        "publication_visibility_key_tail_sha256": _stable_json_sha256(
            publication_visibility_key_tail
        ),
        "publication_visibility_summary_sha256": _stable_json_sha256(
            plan.publication_visibility["summary"]
        ),
        "publication_tag_publish_decision_key_count": len(expected_tag_publish_decision),
        "publication_tag_publish_decision_sha256": _stable_json_sha256(
            expected_tag_publish_decision
        ),
        "publication_tag_publish_decision_first_key": tag_publish_decision_key_boundary[
            "first_key"
        ],
        "publication_tag_publish_decision_last_key": tag_publish_decision_key_boundary[
            "last_key"
        ],
        "publication_tag_publish_decision_key_boundary_sha256": _stable_json_sha256(
            tag_publish_decision_key_boundary
        ),
        "publication_tag_publish_decision_key_preview_count": len(
            tag_publish_decision_key_preview
        ),
        "publication_tag_publish_decision_key_preview": list(
            tag_publish_decision_key_preview
        ),
        "publication_tag_publish_decision_key_preview_sha256": _stable_json_sha256(
            tag_publish_decision_key_preview
        ),
        "publication_tag_publish_decision_key_tail_count": len(
            tag_publish_decision_key_tail
        ),
        "publication_tag_publish_decision_key_tail": list(
            tag_publish_decision_key_tail
        ),
        "publication_tag_publish_decision_key_tail_sha256": _stable_json_sha256(
            tag_publish_decision_key_tail
        ),
        "publication_tag_publish_decision_status": "blocked_by_worktree",
        "publication_tag_can_push": False,
        "publication_tag_required_action_sha256": _stable_json_sha256(
            expected_tag_publish_decision["required_action"]
        ),
        "blocker_count": 2,
        "blockers_sha256": _stable_json_sha256(plan.blockers),
        "blocker_first_item": blocker_boundary["first_item"],
        "blocker_last_item": blocker_boundary["last_item"],
        "blocker_boundary_sha256": _stable_json_sha256(blocker_boundary),
        "blocker_preview_count": len(blocker_preview),
        "blocker_preview": list(blocker_preview),
        "blocker_preview_sha256": _stable_json_sha256(blocker_preview),
        "blocker_tail_count": len(blocker_tail),
        "blocker_tail": list(blocker_tail),
        "blocker_tail_sha256": _stable_json_sha256(blocker_tail),
        "next_action_count": len(plan.next_actions),
        "next_actions_sha256": _stable_json_sha256(plan.next_actions),
        "next_action_first_item": next_action_boundary["first_item"],
        "next_action_last_item": next_action_boundary["last_item"],
        "next_action_boundary_sha256": _stable_json_sha256(next_action_boundary),
        "next_action_preview_count": len(next_action_preview),
        "next_action_preview": list(next_action_preview),
        "next_action_preview_sha256": _stable_json_sha256(next_action_preview),
        "next_action_tail_count": len(next_action_tail),
        "next_action_tail": list(next_action_tail),
        "next_action_tail_sha256": _stable_json_sha256(next_action_tail),
        "publication_next_action_count": 3,
        "publication_next_actions_sha256": _stable_json_sha256(plan.publication_next_actions),
        "publication_next_action_first_item": plan.publication_next_actions[0],
        "publication_next_action_last_item": plan.publication_next_actions[-1],
        "publication_next_action_boundary_sha256": _stable_json_sha256(
            {
                "first_item": plan.publication_next_actions[0],
                "last_item": plan.publication_next_actions[-1],
            }
        ),
        "publication_next_action_preview_count": len(publication_next_action_preview),
        "publication_next_action_preview": list(publication_next_action_preview),
        "publication_next_action_preview_sha256": _stable_json_sha256(
            publication_next_action_preview
        ),
        "publication_next_action_tail_count": len(publication_next_action_tail),
        "publication_next_action_tail": list(publication_next_action_tail),
        "publication_next_action_tail_sha256": _stable_json_sha256(
            publication_next_action_tail
        ),
        "publication_primary_next_action": plan.publication_next_actions[0],
        "publication_handoff_key_count": len(expected_publication_handoff),
        "publication_handoff_schema_version": expected_publication_handoff["schema_version"],
        "publication_handoff_first_key": "schema_version",
        "publication_handoff_last_key": "publish_script_command_sha256",
        "publication_handoff_key_boundary_sha256": _stable_json_sha256(
            {
                "first_key": "schema_version",
                "last_key": "publish_script_command_sha256",
            }
        ),
        "publication_handoff_key_preview_count": len(publication_handoff_key_preview),
        "publication_handoff_key_preview": list(publication_handoff_key_preview),
        "publication_handoff_key_preview_sha256": _stable_json_sha256(
            publication_handoff_key_preview
        ),
        "publication_handoff_key_tail_count": len(publication_handoff_key_tail),
        "publication_handoff_key_tail": list(publication_handoff_key_tail),
        "publication_handoff_key_tail_sha256": _stable_json_sha256(
            publication_handoff_key_tail
        ),
        "publication_handoff_sha256": _stable_json_sha256(expected_publication_handoff),
        "publication_handoff_candidate_issue_gate_primary_reason_code": (
            expected_publication_handoff["candidate_issue_gate_primary_reason_code"]
        ),
        "publication_handoff_candidate_issue_gate_primary_reason_description": (
            expected_publication_handoff["candidate_issue_gate_primary_reason_description"]
        ),
        "publication_handoff_candidate_issue_gate_primary_required_action": (
            expected_publication_handoff["candidate_issue_gate_primary_required_action"]
        ),
        "commit_cadence_status": "needs_more_commit_days",
        "commit_cadence_commit_day_count": 2,
        "commit_cadence_min_commit_days": 3,
        "commit_cadence_missing_commit_days": 1,
        "commit_cadence_next_action_count": 1,
        "commit_cadence_primary_next_action": (
            "Ship verified slices on `1` more unique commit days this week."
        ),
        "commit_cadence_commit_days_sha256": _stable_json_sha256([]),
        "commit_cadence_next_actions_sha256": _stable_json_sha256(
            ["Ship verified slices on `1` more unique commit days this week."]
        ),
        "publication_ref_context_key_count": len(plan.publication_ref_context),
        "publication_ref_context_sha256": _stable_json_sha256(plan.publication_ref_context),
        "publication_ref_context_first_key": "repo_root",
        "publication_ref_context_last_key": "remote_checked",
        "publication_ref_context_key_boundary_sha256": _stable_json_sha256(
            {
                "first_key": "repo_root",
                "last_key": "remote_checked",
            }
        ),
        "publication_ref_context_key_preview_count": len(
            publication_ref_context_key_preview
        ),
        "publication_ref_context_key_preview": list(
            publication_ref_context_key_preview
        ),
        "publication_ref_context_key_preview_sha256": _stable_json_sha256(
            publication_ref_context_key_preview
        ),
        "publication_ref_context_key_tail_count": len(
            publication_ref_context_key_tail
        ),
        "publication_ref_context_key_tail": list(publication_ref_context_key_tail),
        "publication_ref_context_key_tail_sha256": _stable_json_sha256(
            publication_ref_context_key_tail
        ),
        "publication_publish_command_count": plan.publication_publish_command_count,
        "publication_publish_commands_sha256": _stable_json_sha256(plan.publication_publish_commands),
        "publication_publish_first_command": plan.publication_publish_commands[0],
        "publication_publish_last_command": plan.publication_publish_commands[-1],
        "publication_publish_command_boundary_sha256": _stable_json_sha256(
            {
                "first_command": plan.publication_publish_commands[0],
                "last_command": plan.publication_publish_commands[-1],
            }
        ),
        "publication_primary_publish_command": plan.publication_publish_commands[0],
        "publication_publish_script_path_sha256": _stable_json_sha256(
            plan.publication_publish_script_path
        ),
        "publication_publish_script_command_sha256": _stable_json_sha256(
            plan.publication_publish_script_command
        ),
        "publication_worktree_status_count": len(plan.publication_worktree_status),
        "publication_worktree_status_sha256": _stable_json_sha256(plan.publication_worktree_status),
        "publication_worktree_status_first_item": plan.publication_worktree_status[0],
        "publication_worktree_status_last_item": plan.publication_worktree_status[-1],
        "publication_worktree_status_boundary_sha256": _stable_json_sha256(
            {
                "first_item": plan.publication_worktree_status[0],
                "last_item": plan.publication_worktree_status[-1],
            }
        ),
        "release_draft_handoff_key_count": len(expected_release_draft_handoff),
        "release_draft_handoff_schema_version": expected_release_draft_handoff["schema_version"],
        "release_draft_handoff_primary_issue": expected_release_draft_handoff["primary_issue"],
        "release_draft_handoff_primary_required_action": (
            expected_release_draft_handoff["primary_required_action"]
        ),
        "release_draft_handoff_first_key": "schema_version",
        "release_draft_handoff_last_key": "target_version",
        "release_draft_handoff_key_boundary_sha256": _stable_json_sha256(
            {
                "first_key": "schema_version",
                "last_key": "target_version",
            }
        ),
        "release_draft_handoff_key_preview_count": len(
            release_draft_handoff_key_preview
        ),
        "release_draft_handoff_key_preview": list(
            release_draft_handoff_key_preview
        ),
        "release_draft_handoff_key_preview_sha256": _stable_json_sha256(
            release_draft_handoff_key_preview
        ),
        "release_draft_handoff_key_tail_count": len(
            release_draft_handoff_key_tail
        ),
        "release_draft_handoff_key_tail": list(release_draft_handoff_key_tail),
        "release_draft_handoff_key_tail_sha256": _stable_json_sha256(
            release_draft_handoff_key_tail
        ),
        "release_draft_handoff_sha256": _stable_json_sha256(expected_release_draft_handoff),
        "release_draft_path": plan.release_draft_path,
        "release_draft_path_sha256": _stable_json_sha256(plan.release_draft_path),
        "release_draft_primary_issue": expected_release_draft_handoff["release_draft_primary_issue"],
        "release_draft_required_action_count": len(
            expected_release_draft_handoff["release_draft_required_actions"]
        ),
        "release_draft_required_actions_sha256": _stable_json_sha256(
            expected_release_draft_handoff["release_draft_required_actions"]
        ),
        "release_draft_first_required_action": (
            "Resolve release draft issue: release draft is missing"
        ),
        "release_draft_last_required_action": (
            "Resolve release draft issue: release draft missing snippet: ## 发版前验证"
        ),
        "release_draft_required_action_boundary_sha256": _stable_json_sha256(
            {
                "first_action": "Resolve release draft issue: release draft is missing",
                "last_action": (
                    "Resolve release draft issue: release draft missing snippet: ## 发版前验证"
                ),
            }
        ),
        "release_draft_required_action_preview_count": len(
            expected_release_draft_handoff["release_draft_required_actions"][:8]
        ),
        "release_draft_required_action_preview": list(
            expected_release_draft_handoff["release_draft_required_actions"][:8]
        ),
        "release_draft_required_action_preview_sha256": _stable_json_sha256(
            expected_release_draft_handoff["release_draft_required_actions"][:8]
        ),
        "release_draft_required_action_tail_count": len(
            expected_release_draft_handoff["release_draft_required_actions"][-8:]
        ),
        "release_draft_required_action_tail": list(
            expected_release_draft_handoff["release_draft_required_actions"][-8:]
        ),
        "release_draft_required_action_tail_sha256": _stable_json_sha256(
            expected_release_draft_handoff["release_draft_required_actions"][-8:]
        ),
        "release_draft_primary_required_action": (
            expected_release_draft_handoff["release_draft_required_actions"][0]
        ),
        "release_draft_issues_sha256": _stable_json_sha256(plan.release_draft_issues),
        "release_draft_first_issue": "release draft is missing",
        "release_draft_last_issue": "release draft missing snippet: ## 发版前验证",
        "release_draft_issue_boundary_sha256": _stable_json_sha256(
            {
                "first_issue": "release draft is missing",
                "last_issue": "release draft missing snippet: ## 发版前验证",
            }
        ),
        "release_draft_issue_preview_count": len(plan.release_draft_issues[:8]),
        "release_draft_issue_preview": list(plan.release_draft_issues[:8]),
        "release_draft_issue_preview_sha256": _stable_json_sha256(
            plan.release_draft_issues[:8]
        ),
        "release_draft_issue_tail_count": len(plan.release_draft_issues[-8:]),
        "release_draft_issue_tail": list(plan.release_draft_issues[-8:]),
        "release_draft_issue_tail_sha256": _stable_json_sha256(
            plan.release_draft_issues[-8:]
        ),
        "validation_command_count": 6,
        "validation_commands_sha256": _stable_json_sha256(expected_validation_commands),
        "validation_first_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
        "validation_last_command": "python scripts/validate_cases.py --strict",
        "validation_command_boundary_sha256": _stable_json_sha256(
            {
                "first_command": (
                    "python scripts/plan_next_iteration.py --target-version 0.16.2 "
                    "--issues-dir /tmp/cliany-candidate-issues"
                ),
                "last_command": "python scripts/validate_cases.py --strict",
            }
        ),
        "validation_command_preview_count": len(expected_validation_commands[:8]),
        "validation_command_preview": list(expected_validation_commands[:8]),
        "validation_command_preview_sha256": _stable_json_sha256(
            expected_validation_commands[:8]
        ),
        "validation_command_tail_count": len(expected_validation_commands[-8:]),
        "validation_command_tail": list(expected_validation_commands[-8:]),
        "validation_command_tail_sha256": _stable_json_sha256(
            expected_validation_commands[-8:]
        ),
        "review_checklist_count": 7,
        "review_checklist_sha256": _stable_json_sha256(expected_review_checklist),
        "review_checklist_first_item": (
            "Confirm the latest local release has been published before creating new candidate work."
        ),
        "review_checklist_last_item": (
            "Do not use real LLM keys or write runtime state into the repository."
        ),
        "review_checklist_boundary_sha256": _stable_json_sha256(
            {
                "first_item": (
                    "Confirm the latest local release has been published before creating new candidate work."
                ),
                "last_item": "Do not use real LLM keys or write runtime state into the repository.",
            }
        ),
        "review_checklist_preview_count": len(expected_review_checklist[:8]),
        "review_checklist_preview": list(expected_review_checklist[:8]),
        "review_checklist_preview_sha256": _stable_json_sha256(
            expected_review_checklist[:8]
        ),
        "review_checklist_tail_count": len(expected_review_checklist[-8:]),
        "review_checklist_tail": list(expected_review_checklist[-8:]),
        "review_checklist_tail_sha256": _stable_json_sha256(
            expected_review_checklist[-8:]
        ),
        "create_issues_safety_contract_key_count": 5,
        "create_issues_safety_contract_sha256": _stable_json_sha256(
            expected_create_issues_safety_contract
        ),
        "create_issues_safety_contract_first_key": "dry_run_supported",
        "create_issues_safety_contract_last_key": "preflight_json",
        "create_issues_safety_contract_key_boundary_sha256": _stable_json_sha256(
            {
                "first_key": "dry_run_supported",
                "last_key": "preflight_json",
            }
        ),
        "create_issues_safety_contract_key_preview_count": len(
            create_issues_safety_contract_keys[:8]
        ),
        "create_issues_safety_contract_key_preview": list(
            create_issues_safety_contract_keys[:8]
        ),
        "create_issues_safety_contract_key_preview_sha256": _stable_json_sha256(
            create_issues_safety_contract_keys[:8]
        ),
        "create_issues_safety_contract_key_tail_count": len(
            create_issues_safety_contract_keys[-8:]
        ),
        "create_issues_safety_contract_key_tail": list(
            create_issues_safety_contract_keys[-8:]
        ),
        "create_issues_safety_contract_key_tail_sha256": _stable_json_sha256(
            create_issues_safety_contract_keys[-8:]
        ),
        "publication_ok": False,
        "publication_visibility_status": "dirty_worktree",
        "publication_branch": "master",
        "publication_upstream": "origin/master",
        "publication_remote": "origin",
        "publication_latest_tag": "v0.16.1",
        "publication_tag_commit": "abc123",
        "publication_local_head": "abc123",
        "publication_upstream_head": "def456",
        "publication_tag_points_at_head": True,
        "publication_tag_commit_in_upstream": False,
        "publication_branch_published": False,
        "publication_tag_published": False,
        "publication_remote_branch_head": None,
        "publication_remote_tag_commit": None,
        "publication_remote_checked": False,
        "publication_ahead_count": 2,
        "publication_behind_count": 0,
        "release_draft_ok": False,
        "release_draft_issue_count": 2,
        "candidate_issue_gate_key_count": len(_blocked_candidate_issue_gate()),
        "candidate_issue_gate_sha256": _stable_json_sha256(_blocked_candidate_issue_gate()),
        "candidate_issue_gate_status": "blocked_by_publication",
        "can_create_issues": False,
        "requires_maintainer_review": True,
        "candidate_issue_gate_summary_sha256": _stable_json_sha256(
            _blocked_candidate_issue_gate()["summary"]
        ),
        "candidate_issue_gate_evidence_key_count": len(candidate_issue_gate_evidence),
        "candidate_issue_gate_evidence_sha256": _stable_json_sha256(candidate_issue_gate_evidence),
        "candidate_issue_gate_evidence_first_key": candidate_issue_gate_evidence_key_boundary[
            "first_key"
        ],
        "candidate_issue_gate_evidence_last_key": candidate_issue_gate_evidence_key_boundary[
            "last_key"
        ],
        "candidate_issue_gate_evidence_key_boundary_sha256": _stable_json_sha256(
            candidate_issue_gate_evidence_key_boundary
        ),
        "candidate_issue_gate_reason_description_count": len(candidate_issue_gate_reason_descriptions),
        "candidate_issue_gate_reason_descriptions_sha256": _stable_json_sha256(
            candidate_issue_gate_reason_descriptions
        ),
        "candidate_issue_gate_reason_code_count": _blocked_candidate_issue_gate()["reason_code_count"],
        "candidate_issue_gate_reason_codes_sha256": _blocked_candidate_issue_gate()["reason_codes_sha256"],
        "candidate_issue_gate_first_reason_code": "publication_not_published",
        "candidate_issue_gate_last_reason_code": "release_draft_issues",
        "candidate_issue_gate_reason_code_boundary_sha256": _stable_json_sha256(
            {
                "first_code": "publication_not_published",
                "last_code": "release_draft_issues",
            }
        ),
        "candidate_issue_gate_primary_reason_code": "publication_not_published",
        "candidate_issue_gate_primary_reason_description": (
            "The latest local release branch or tag is not visible upstream."
        ),
        "candidate_issue_gate_required_action_count": _blocked_candidate_issue_gate()["required_action_count"],
        "candidate_issue_gate_required_actions_sha256": _blocked_candidate_issue_gate()["required_actions_sha256"],
        "candidate_issue_gate_first_required_action": (
            "Commit, stash, or discard local worktree changes before publishing release refs."
        ),
        "candidate_issue_gate_last_required_action": (
            "Resolve release draft issue: release draft missing snippet: ## 发版前验证"
        ),
        "candidate_issue_gate_required_action_boundary_sha256": _stable_json_sha256(
            {
                "first_action": (
                    "Commit, stash, or discard local worktree changes before publishing release refs."
                ),
                "last_action": (
                    "Resolve release draft issue: release draft missing snippet: ## 发版前验证"
                ),
            }
        ),
        "candidate_issue_gate_primary_required_action": (
            "Commit, stash, or discard local worktree changes before publishing release refs."
        ),
        "dry_run_supported": True,
        "preflight_required": True,
    }

    assert "## Scope: promote candidate case `pypi-project-search`" in body
    assert "## Reproduction Context" in body
    assert "- Target URL: https://pypi.org/search/?q=cliany-site" in body
    assert "- Candidate commands:\n  - `cliany-site explore" in body
    assert "- Offline validation commands:\n  - `python scripts/validate_cases.py --strict`" in body
    assert 'cliany-site explore "https://pypi.org" "search Python packages" --json' in body
    assert "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md" in body
    assert "## Promotion Command Plan" in body
    assert (
        '`adapter_package`: `cliany-site explore "https://pypi.org" "search Python packages" --json`'
        in body
    )
    assert (
        "`metadata_validation`: `python scripts/validate_cases.py "
        "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`"
        in body
    )
    assert (
        "`online_smoke`: `cliany-site pypi.org search-projects --query cliany-site --limit 5 --json`"
        in body
    )
    assert "## Evidence Bundle" in body
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle" in body
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in body
    assert "Attach or paste the JSON output in the issue once evidence changes." in body
    assert "Candidate package validation command" in body
    assert (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
        in body
    )
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
    assert metadata[0]["promotion_evidence"] == _promotion_evidence(
        "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        "Run read-only PyPI search smoke.",
    )
    assert metadata[0]["promotion_evidence_primary_task"] == {
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
    }
    assert metadata[0]["evidence_bundle_primary_next_task"] == {
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
    }
    assert metadata[0]["candidate_package_validation_command"] == (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
    )
    assert metadata[0]["promotion_command_plan"] == _pypi_promotion_command_plan()
    assert (
        metadata[0]["evidence_bundle_command"]
        == "cliany-site cases --case-id pypi-project-search --evidence-bundle"
    )
    assert (
        metadata[0]["evidence_bundle_json_command"]
        == "cliany-site cases --case-id pypi-project-search --evidence-bundle --json"
    )
    assert metadata[0]["issue_body_name"] == "pypi-project-search.md"
    assert metadata[0]["issue_body_file"].endswith("pypi-project-search.md")
    assert "gh issue create" in metadata[0]["create_command"]
    assert "--label case-proposal" in metadata[0]["create_command"]
    assert "--label 'good first issue'" in metadata[0]["create_command"]
    assert artifact_manifest == {
        "schema_version": plan_next_iteration.ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "target_version": "0.16.2",
        "artifact_bundle_summary": artifact_bundle_summary,
        "candidate_count": 2,
        "candidate_cases": ["pypi-project-search", "npm-package-search"],
        "case_promotion_evidence_summary": plan.case_promotion_evidence_summary,
        "case_promotion_command_plan_summary": plan.case_promotion_command_plan_summary,
        "blockers": ["release draft validation failed", "latest local release is not published"],
        "next_actions": plan.next_actions,
        "next_action_count": len(plan.next_actions),
        "next_actions_sha256": _stable_json_sha256(plan.next_actions),
        "primary_next_action": plan.next_actions[0],
        "commit_cadence": plan.commit_cadence,
        "candidate_issue_gate": _blocked_candidate_issue_gate(),
        "publication_ok": False,
        "publication_visibility": {
            "status": "dirty_worktree",
            "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
        },
        "publication_tag_publish_decision": expected_tag_publish_decision,
        "publication_next_actions": [
            "Commit, stash, or discard local worktree changes before publishing release refs.",
            "Push `master` to `origin`; local branch is ahead by `2` commits.",
            "Push tag `v0.16.1` after the branch is published.",
        ],
        "publication_publish_commands": ["python scripts/check_release_publication.py --json"],
        "publication_ref_context": {
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
            "tag_points_at_head": True,
            "tag_commit_in_upstream": False,
            "branch_published": False,
            "tag_published": False,
            "remote_branch_head": None,
            "remote_tag_commit": None,
            "remote_checked": False,
        },
        "publication_worktree_clean": False,
        "publication_worktree_status": [" M CHANGELOG.md"],
        "publication_publish_script_path": "/tmp/cliany-publish-release.sh",
        "publication_publish_script_path_sha256": _stable_json_sha256(
            "/tmp/cliany-publish-release.sh"
        ),
        "publication_publish_script_command": (
            "python scripts/check_release_publication.py --json "
            "--publish-script /tmp/cliany-publish-release.sh"
        ),
        "publication_publish_script_command_sha256": _stable_json_sha256(
            "python scripts/check_release_publication.py --json "
            "--publish-script /tmp/cliany-publish-release.sh"
        ),
        "release_draft_path": "docs/releases/v0.16.2-draft.md",
        "release_draft_issues": [
            "release draft is missing",
            "release draft missing snippet: ## 发版前验证",
        ],
        "issue_artifacts_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--issues-dir /tmp/cliany-candidate-issues"
        ),
        "plan_report_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 "
            "--report /tmp/cliany-next-iteration.md"
        ),
        "create_issues_dry_run_command": f"CLIANY_CREATE_ISSUES_DRY_RUN=1 {issues_dir / 'create-issues.sh'}",
        "create_issues_safety": create_issues_safety,
        "issue_body_inventory": issue_body_inventory,
        "issue_body_summary": issue_body_summary,
        "issue_metadata_summary": issue_metadata_summary,
        "files": expected_artifact_files,
        "review_order": review_order,
        "review_checklist": [
            "Confirm the latest local release has been published before creating new candidate work.",
            "Confirm release draft issues are resolved or intentionally deferred before tagging the target version.",
            "Confirm Publication Next Actions are resolved or intentionally deferred before running create-issues.sh.",
                (
                    "Confirm issue-metadata.json has the expected target URL, candidate commands, "
                    "offline validation commands, candidate_package_validation_command, "
                    "and promotion_command_plan for each case."
                ),
            "Review each body file for scope, tasks, validation evidence, and non-goals.",
            (
                "Keep cases as candidate until adapter package, metadata validation, "
                "and online smoke evidence are complete."
            ),
            "Do not use real LLM keys or write runtime state into the repository.",
        ],
        "validation_commands": [
            (
                "python scripts/plan_next_iteration.py --target-version 0.16.2 "
                "--issues-dir /tmp/cliany-candidate-issues"
            ),
            (
                "python scripts/plan_next_iteration.py --target-version 0.16.2 "
                "--report /tmp/cliany-next-iteration.md"
            ),
            "python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
            "python scripts/release_readiness.py --target-version 0.16.2 --json",
            "python scripts/check_release_publication.py --json",
            "python scripts/validate_cases.py --strict",
        ],
    }
    assert list(artifact_manifest) == list(plan_next_iteration.ARTIFACT_MANIFEST_KEYS)
    assert list(artifact_manifest["artifact_bundle_summary"]) == list(
        plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS
    )
    assert artifact_manifest["artifact_bundle_summary"]["artifact_bundle_summary_key_preview"] == list(
        plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS[
            : artifact_manifest["artifact_bundle_summary"]["artifact_bundle_summary_key_preview_count"]
        ]
    )
    assert artifact_manifest["artifact_bundle_summary"]["artifact_bundle_summary_key_tail"] == list(
        plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS[
            -artifact_manifest["artifact_bundle_summary"]["artifact_bundle_summary_key_tail_count"] :
        ]
    )
    assert artifact_manifest["artifact_bundle_summary"]["artifact_bundle_summary_first_key"] == list(
        artifact_manifest["artifact_bundle_summary"]
    )[0]
    assert artifact_manifest["artifact_bundle_summary"]["artifact_bundle_summary_last_key"] == list(
        artifact_manifest["artifact_bundle_summary"]
    )[-1]
    assert artifact_manifest["artifact_bundle_summary"]["artifact_manifest_first_key"] == list(
        artifact_manifest
    )[0]
    assert artifact_manifest["artifact_bundle_summary"]["artifact_manifest_last_key"] == list(
        artifact_manifest
    )[-1]
    assert artifact_manifest["artifact_bundle_summary"]["artifact_manifest_key_preview"] == list(
        artifact_manifest
    )[: artifact_manifest["artifact_bundle_summary"]["artifact_manifest_key_preview_count"]]
    assert artifact_manifest["artifact_bundle_summary"]["artifact_manifest_key_tail"] == list(
        artifact_manifest
    )[-artifact_manifest["artifact_bundle_summary"]["artifact_manifest_key_tail_count"] :]
    assert {
        key: value for key, value in artifact_manifest.items() if key != "artifact_bundle_summary"
    } == artifact_manifest_payload
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_manifest_payload_first_key"
    ] == list(artifact_manifest_payload)[0]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_manifest_payload_last_key"
    ] == list(artifact_manifest_payload)[-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_manifest_payload_key_preview"
    ] == list(artifact_manifest_payload)[
        : artifact_manifest["artifact_bundle_summary"][
            "artifact_manifest_payload_key_preview_count"
        ]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_manifest_payload_key_tail"
    ] == list(artifact_manifest_payload)[
        -artifact_manifest["artifact_bundle_summary"][
            "artifact_manifest_payload_key_tail_count"
        ] :
    ]
    assert artifact_manifest["artifact_bundle_summary"]["candidate_cases_preview"] == artifact_manifest[
        "candidate_cases"
    ][: artifact_manifest["artifact_bundle_summary"]["candidate_cases_preview_count"]]
    assert artifact_manifest["artifact_bundle_summary"]["candidate_cases_tail"] == artifact_manifest[
        "candidate_cases"
    ][-artifact_manifest["artifact_bundle_summary"]["candidate_cases_tail_count"] :]
    assert artifact_manifest["artifact_bundle_summary"]["candidate_cases_first_case"] == artifact_manifest[
        "candidate_cases"
    ][0]
    assert artifact_manifest["artifact_bundle_summary"]["candidate_cases_last_case"] == artifact_manifest[
        "candidate_cases"
    ][-1]
    assert artifact_manifest["case_promotion_evidence_summary"] == plan.case_promotion_evidence_summary
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_inventory_preview"
    ] == artifact_manifest["issue_body_inventory"][
        : artifact_manifest["artifact_bundle_summary"][
            "issue_body_inventory_preview_count"
        ]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_inventory_tail"
    ] == artifact_manifest["issue_body_inventory"][
        -artifact_manifest["artifact_bundle_summary"]["issue_body_inventory_tail_count"] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_inventory_first_entry"
    ] == artifact_manifest["issue_body_inventory"][0]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_inventory_last_entry"
    ] == artifact_manifest["issue_body_inventory"][-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_summary_key_count"
    ] == len(artifact_manifest["issue_body_summary"])
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_summary_first_key"
    ] == list(artifact_manifest["issue_body_summary"])[0]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_summary_last_key"
    ] == list(artifact_manifest["issue_body_summary"])[-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_summary_key_preview"
    ] == list(artifact_manifest["issue_body_summary"])[
        : artifact_manifest["artifact_bundle_summary"][
            "issue_body_summary_key_preview_count"
        ]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_body_summary_key_tail"
    ] == list(artifact_manifest["issue_body_summary"])[
        -artifact_manifest["artifact_bundle_summary"][
            "issue_body_summary_key_tail_count"
        ] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "review_order_preview"
    ] == artifact_manifest["review_order"][
        : artifact_manifest["artifact_bundle_summary"][
            "review_order_preview_count"
        ]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "review_order_first_item"
    ] == artifact_manifest["review_order"][0]
    assert artifact_manifest["artifact_bundle_summary"][
        "review_order_last_item"
    ] == artifact_manifest["review_order"][-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "review_order_tail"
    ] == artifact_manifest["review_order"][
        -artifact_manifest["artifact_bundle_summary"][
            "review_order_tail_count"
        ] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_metadata_preview"
    ] == artifact_manifest["issue_metadata_summary"]["metadata_preview"]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_metadata_first_item"
    ] == artifact_manifest["issue_metadata_summary"]["metadata_first_item"]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_metadata_last_item"
    ] == artifact_manifest["issue_metadata_summary"]["metadata_last_item"]
    assert artifact_manifest["artifact_bundle_summary"][
        "issue_metadata_tail"
    ] == artifact_manifest["issue_metadata_summary"]["metadata_tail"]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_files_first_key"
    ] == list(artifact_manifest["files"])[0]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_files_last_key"
    ] == list(artifact_manifest["files"])[-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_files_key_preview"
    ] == list(artifact_manifest["files"])[
        : artifact_manifest["artifact_bundle_summary"][
            "artifact_files_key_preview_count"
        ]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "artifact_files_key_tail"
    ] == list(artifact_manifest["files"])[
        -artifact_manifest["artifact_bundle_summary"][
            "artifact_files_key_tail_count"
        ] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "publication_visibility_first_key"
    ] == list(artifact_manifest["publication_visibility"])[0]
    assert artifact_manifest["artifact_bundle_summary"][
        "publication_visibility_last_key"
    ] == list(artifact_manifest["publication_visibility"])[-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "publication_visibility_key_preview"
    ] == list(artifact_manifest["publication_visibility"])[
        : artifact_manifest["artifact_bundle_summary"][
            "publication_visibility_key_preview_count"
        ]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "publication_visibility_key_tail"
    ] == list(artifact_manifest["publication_visibility"])[
        -artifact_manifest["artifact_bundle_summary"][
            "publication_visibility_key_tail_count"
        ] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "blocker_preview"
    ] == artifact_manifest["blockers"][
        : artifact_manifest["artifact_bundle_summary"]["blocker_preview_count"]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "blocker_tail"
    ] == artifact_manifest["blockers"][
        -artifact_manifest["artifact_bundle_summary"]["blocker_tail_count"] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "blocker_first_item"
    ] == artifact_manifest["blockers"][0]
    assert artifact_manifest["artifact_bundle_summary"][
        "blocker_last_item"
    ] == artifact_manifest["blockers"][-1]
    assert artifact_manifest["artifact_bundle_summary"][
        "next_action_preview"
    ] == artifact_manifest["next_actions"][
        : artifact_manifest["artifact_bundle_summary"]["next_action_preview_count"]
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "next_action_tail"
    ] == artifact_manifest["next_actions"][
        -artifact_manifest["artifact_bundle_summary"]["next_action_tail_count"] :
    ]
    assert artifact_manifest["artifact_bundle_summary"][
        "next_action_first_item"
    ] == artifact_manifest["next_actions"][0]
    assert artifact_manifest["artifact_bundle_summary"][
        "next_action_last_item"
    ] == artifact_manifest["next_actions"][-1]
    assert publication_handoff == expected_publication_handoff
    assert release_draft_handoff == expected_release_draft_handoff
    assert "gh issue create" in script
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in script
    assert 'cd "$REPO_ROOT"' in script
    assert "CLIANY_CREATE_ISSUES_DRY_RUN" in script
    assert "Dry run: publication preflight and gh issue create are not executed." in script
    assert "cat <<'CLIANY_ISSUE_COMMANDS'" in script
    assert "CLIANY_ISSUE_COMMANDS" in script
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
    assert (
        "`artifact-manifest.json`: schema version, candidate cases, promotion evidence summary,"
    ) in readme
    assert "review checklist, candidate issue gate, publication status" in readme
    assert "release draft" in readme
    assert "handoff, reproduction" in readme
    assert "plan report command" in readme
    assert "body file name" in readme
    assert "`publication-handoff.json`: publication status, candidate issue gate, visibility" in readme
    assert "`release-draft-handoff.json`: schema version, target version" in readme
    assert "## Candidate Summary" in readme
    assert (
        "| Case | Issue Body | Target URL | Candidate Commands | Offline Validation Commands | "
        "Primary Evidence Task | Evidence Bundle Primary Next Task | Candidate Package Validation | "
        "Evidence Bundle | Evidence Bundle JSON |"
    ) in readme
    assert (
        "| `pypi-project-search` | `pypi-project-search.md` | "
        "https://pypi.org/search/?q=cliany-site | 2 | 2 | "
        "`adapter_package` | `adapter_package` | "
        "`python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict` | "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle` | "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle --json` |"
    ) in readme
    assert "## Candidate Promotion Evidence Summary" in readme
    assert "| pending_count | `6` |" in readme
    assert "| primary_next_action | `Generate pypi.org-<version>.cliany-adapter.tar.gz.` |" in readme
    assert (
        "| `pypi-project-search` | `adapter_package` | `pending` | - | "
        "Generate pypi.org-<version>.cliany-adapter.tar.gz. |"
    ) in readme
    assert "## Issue Body Inventory" in readme
    assert "| Case | Issue Body | Bytes | SHA-256 |" in readme
    assert (
        f"| `pypi-project-search` | `pypi-project-search.md` | "
        f"{issue_body_inventory[0]['byte_count']} | `{issue_body_inventory[0]['sha256']}` |"
    ) in readme
    assert "## Issue Body Summary" in readme
    assert f"body_count: `{issue_body_summary['body_count']}`" in readme
    assert f"total_byte_count: `{issue_body_summary['total_byte_count']}`" in readme
    assert f"inventory_sha256: `{issue_body_summary['inventory_sha256']}`" in readme
    assert "## Artifact Bundle Summary" in readme
    assert (
        f"artifact_bundle_summary_key_count: `{len(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS)}`"
    ) in readme
    assert (
        "artifact_bundle_summary_keys_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEYS)}`"
    ) in readme
    assert (
        "artifact_bundle_summary_key_preview_count: "
        f"`{len(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW)}`"
    ) in readme
    assert "artifact_bundle_summary_key_preview: " in readme
    assert (
        "artifact_bundle_summary_key_preview_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_PREVIEW)}`"
    ) in readme
    assert (
        "artifact_bundle_summary_key_tail_count: "
        f"`{len(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL)}`"
    ) in readme
    assert "artifact_bundle_summary_key_tail: " in readme
    assert (
        "artifact_bundle_summary_key_tail_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_TAIL)}`"
    ) in readme
    assert (
        "artifact_bundle_summary_first_key: "
        f"`{plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY['first_key']}`"
    ) in readme
    assert (
        "artifact_bundle_summary_last_key: "
        f"`{plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY['last_key']}`"
    ) in readme
    assert (
        "artifact_bundle_summary_key_boundary_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_BUNDLE_SUMMARY_KEY_BOUNDARY)}`"
    ) in readme
    assert (
        "artifact_manifest_schema_version: "
        f"`{plan_next_iteration.ARTIFACT_MANIFEST_SCHEMA_VERSION}`"
    ) in readme
    assert (
        f"artifact_manifest_key_count: `{len(plan_next_iteration.ARTIFACT_MANIFEST_KEYS)}`"
    ) in readme
    assert (
        "artifact_manifest_keys_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_KEYS)}`"
    ) in readme
    assert (
        "artifact_manifest_first_key: "
        f"`{plan_next_iteration.ARTIFACT_MANIFEST_KEY_BOUNDARY['first_key']}`"
    ) in readme
    assert (
        "artifact_manifest_last_key: "
        f"`{plan_next_iteration.ARTIFACT_MANIFEST_KEY_BOUNDARY['last_key']}`"
    ) in readme
    assert (
        "artifact_manifest_key_boundary_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_KEY_BOUNDARY)}`"
    ) in readme
    assert (
        "artifact_manifest_key_preview_count: "
        f"`{len(plan_next_iteration.ARTIFACT_MANIFEST_KEY_PREVIEW)}`"
    ) in readme
    assert "artifact_manifest_key_preview: " in readme
    assert (
        "artifact_manifest_key_preview_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_KEY_PREVIEW)}`"
    ) in readme
    assert (
        "artifact_manifest_key_tail_count: "
        f"`{len(plan_next_iteration.ARTIFACT_MANIFEST_KEY_TAIL)}`"
    ) in readme
    assert "artifact_manifest_key_tail: " in readme
    assert (
        "artifact_manifest_key_tail_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_KEY_TAIL)}`"
    ) in readme
    assert f"artifact_manifest_payload_key_count: `{len(artifact_manifest_payload)}`" in readme
    assert (
        "artifact_manifest_payload_first_key: "
        f"`{plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY['first_key']}`"
    ) in readme
    assert (
        "artifact_manifest_payload_last_key: "
        f"`{plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY['last_key']}`"
    ) in readme
    assert (
        "artifact_manifest_payload_key_boundary_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_BOUNDARY)}`"
    ) in readme
    assert (
        "artifact_manifest_payload_key_preview_count: "
        f"`{len(plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW)}`"
    ) in readme
    assert "artifact_manifest_payload_key_preview: " in readme
    assert (
        "artifact_manifest_payload_key_preview_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_PREVIEW)}`"
    ) in readme
    assert (
        "artifact_manifest_payload_key_tail_count: "
        f"`{len(plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL)}`"
    ) in readme
    assert "artifact_manifest_payload_key_tail: " in readme
    assert (
        "artifact_manifest_payload_key_tail_sha256: "
        f"`{_stable_json_sha256(plan_next_iteration.ARTIFACT_MANIFEST_PAYLOAD_KEY_TAIL)}`"
    ) in readme
    assert (
        "artifact_manifest_payload_sha256: "
        f"`{_stable_json_sha256(artifact_manifest_payload)}`"
    ) in readme
    assert "target_version: `0.16.2`" in readme
    assert "candidate_count: `2`" in readme
    assert "candidate_cases_first_case: `pypi-project-search`" in readme
    assert "candidate_cases_last_case: `npm-package-search`" in readme
    assert (
        "candidate_cases_boundary_sha256: "
        f"`{_stable_json_sha256({'first_case': 'pypi-project-search', 'last_case': 'npm-package-search'})}`"
    ) in readme
    assert "candidate_cases_preview_count: `2`" in readme
    assert "candidate_cases_preview: " in readme
    assert (
        "candidate_cases_preview_sha256: "
        f"`{_stable_json_sha256(['pypi-project-search', 'npm-package-search'])}`"
    ) in readme
    assert "candidate_cases_tail_count: `2`" in readme
    assert "candidate_cases_tail: " in readme
    assert (
        "candidate_cases_tail_sha256: "
        f"`{_stable_json_sha256(['pypi-project-search', 'npm-package-search'])}`"
    ) in readme
    assert "candidate_cases_sha256: `" in readme
    assert f"candidate_cases_sha256: `{artifact_bundle_summary['candidate_cases_sha256']}`" in readme
    assert (
        "case_promotion_evidence_summary_key_count: "
        f"`{artifact_bundle_summary['case_promotion_evidence_summary_key_count']}`"
    ) in readme
    assert (
        "case_promotion_evidence_summary_keys_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_summary_keys_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_summary_first_key: `candidate_count`" in readme
    assert "case_promotion_evidence_summary_last_key: `primary_next_action`" in readme
    assert "primary_task_detail" in readme
    assert (
        "case_promotion_evidence_summary_key_boundary_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_summary_key_boundary_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_summary_key_preview_count: `8`" in readme
    assert "case_promotion_evidence_summary_key_preview: " in readme
    assert (
        "case_promotion_evidence_summary_key_preview_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_summary_key_preview_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_summary_key_tail_count: `8`" in readme
    assert "case_promotion_evidence_summary_key_tail: " in readme
    assert (
        "case_promotion_evidence_summary_key_tail_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_summary_key_tail_sha256']}`"
    ) in readme
    assert (
        "case_promotion_evidence_summary_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_summary_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_candidate_count: `2`" in readme
    assert "case_promotion_evidence_task_count: `6`" in readme
    assert "case_promotion_evidence_pending_count: `6`" in readme
    assert "case_promotion_evidence_blocked_count: `0`" in readme
    assert "case_promotion_evidence_complete_count: `0`" in readme
    assert (
        "case_promotion_evidence_primary_next_action: "
        "`Generate pypi.org-<version>.cliany-adapter.tar.gz.`"
    ) in readme
    assert "case_promotion_evidence_primary_case_id: `pypi-project-search`" in readme
    assert "case_promotion_evidence_primary_task: `adapter_package`" in readme
    assert "case_promotion_evidence_primary_status: `pending`" in readme
    assert (
        "case_promotion_evidence_primary_evidence_sha256: "
        f"`{_stable_json_sha256('')}`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_detail_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_detail_sha256']}`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_next_task_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_next_task_sha256']}`"
    ) in readme
    assert (
        "case_promotion_command_plan_summary_sha256: "
        f"`{artifact_bundle_summary['case_promotion_command_plan_summary_sha256']}`"
    ) in readme
    assert "case_promotion_command_plan_candidate_count: `2`" in readme
    assert "case_promotion_command_plan_command_count: `6`" in readme
    assert "case_promotion_command_plan_missing_command_count: `1`" in readme
    assert "case_promotion_command_plan_all_declared: `false`" in readme
    assert (
        "issue_body_inventory_preview_count: "
        f"`{artifact_bundle_summary['issue_body_inventory_preview_count']}`"
    ) in readme
    assert "issue_body_inventory_preview: " in readme
    assert (
        "issue_body_inventory_preview_sha256: "
        f"`{artifact_bundle_summary['issue_body_inventory_preview_sha256']}`"
    ) in readme
    assert "issue_body_inventory_first_entry: " in readme
    assert "issue_body_inventory_last_entry: " in readme
    assert (
        "issue_body_inventory_boundary_sha256: "
        f"`{artifact_bundle_summary['issue_body_inventory_boundary_sha256']}`"
    ) in readme
    assert (
        "issue_body_inventory_tail_count: "
        f"`{artifact_bundle_summary['issue_body_inventory_tail_count']}`"
    ) in readme
    assert "issue_body_inventory_tail: " in readme
    assert (
        "issue_body_inventory_tail_sha256: "
        f"`{artifact_bundle_summary['issue_body_inventory_tail_sha256']}`"
    ) in readme
    assert (
        "issue_body_summary_key_count: "
        f"`{artifact_bundle_summary['issue_body_summary_key_count']}`"
    ) in readme
    assert (
        "issue_body_summary_keys_sha256: "
        f"`{artifact_bundle_summary['issue_body_summary_keys_sha256']}`"
    ) in readme
    assert (
        "issue_body_summary_first_key: "
        f"`{artifact_bundle_summary['issue_body_summary_first_key']}`"
    ) in readme
    assert (
        "issue_body_summary_last_key: "
        f"`{artifact_bundle_summary['issue_body_summary_last_key']}`"
    ) in readme
    assert (
        "issue_body_summary_key_boundary_sha256: "
        f"`{artifact_bundle_summary['issue_body_summary_key_boundary_sha256']}`"
    ) in readme
    assert (
        "issue_body_summary_key_preview_count: "
        f"`{artifact_bundle_summary['issue_body_summary_key_preview_count']}`"
    ) in readme
    assert "issue_body_summary_key_preview: " in readme
    assert (
        "issue_body_summary_key_preview_sha256: "
        f"`{artifact_bundle_summary['issue_body_summary_key_preview_sha256']}`"
    ) in readme
    assert (
        "issue_body_summary_key_tail_count: "
        f"`{artifact_bundle_summary['issue_body_summary_key_tail_count']}`"
    ) in readme
    assert "issue_body_summary_key_tail: " in readme
    assert (
        "issue_body_summary_key_tail_sha256: "
        f"`{artifact_bundle_summary['issue_body_summary_key_tail_sha256']}`"
    ) in readme
    assert f"issue_body_summary_sha256: `{artifact_bundle_summary['issue_body_summary_sha256']}`" in readme
    assert "review_item_count: `7`" in readme
    assert f"review_order_sha256: `{review_order_sha256}`" in readme
    assert (
        "review_order_first_item: "
        f"`{artifact_bundle_summary['review_order_first_item']}`"
    ) in readme
    assert (
        "review_order_last_item: "
        f"`{artifact_bundle_summary['review_order_last_item']}`"
    ) in readme
    assert (
        "review_order_boundary_sha256: "
        f"`{artifact_bundle_summary['review_order_boundary_sha256']}`"
    ) in readme
    assert (
        "review_order_preview_count: "
        f"`{artifact_bundle_summary['review_order_preview_count']}`"
    ) in readme
    assert "review_order_preview: " in readme
    assert (
        "review_order_preview_sha256: "
        f"`{artifact_bundle_summary['review_order_preview_sha256']}`"
    ) in readme
    assert (
        "review_order_tail_count: "
        f"`{artifact_bundle_summary['review_order_tail_count']}`"
    ) in readme
    assert "review_order_tail: " in readme
    assert (
        "review_order_tail_sha256: "
        f"`{artifact_bundle_summary['review_order_tail_sha256']}`"
    ) in readme
    assert f"issue_metadata_count: `{issue_metadata_summary['metadata_count']}`" in readme
    assert f"issue_metadata_sha256: `{issue_metadata_summary['metadata_sha256']}`" in readme
    assert "issue_metadata_first_item: " in readme
    assert "issue_metadata_last_item: " in readme
    assert (
        "issue_metadata_boundary_sha256: "
        f"`{artifact_bundle_summary['issue_metadata_boundary_sha256']}`"
    ) in readme
    assert (
        "issue_metadata_preview_count: "
        f"`{artifact_bundle_summary['issue_metadata_preview_count']}`"
    ) in readme
    assert "issue_metadata_preview: " in readme
    assert (
        "issue_metadata_preview_sha256: "
        f"`{artifact_bundle_summary['issue_metadata_preview_sha256']}`"
    ) in readme
    assert (
        "issue_metadata_tail_count: "
        f"`{artifact_bundle_summary['issue_metadata_tail_count']}`"
    ) in readme
    assert "issue_metadata_tail: " in readme
    assert (
        "issue_metadata_tail_sha256: "
        f"`{artifact_bundle_summary['issue_metadata_tail_sha256']}`"
    ) in readme
    assert "artifact_files_key_count: `6`" in readme
    assert f"artifact_files_sha256: `{artifact_bundle_summary['artifact_files_sha256']}`" in readme
    assert (
        "artifact_files_first_key: "
        f"`{artifact_bundle_summary['artifact_files_first_key']}`"
    ) in readme
    assert (
        "artifact_files_last_key: "
        f"`{artifact_bundle_summary['artifact_files_last_key']}`"
    ) in readme
    assert (
        "artifact_files_key_boundary_sha256: "
        f"`{artifact_bundle_summary['artifact_files_key_boundary_sha256']}`"
    ) in readme
    assert (
        "artifact_files_key_preview_count: "
        f"`{artifact_bundle_summary['artifact_files_key_preview_count']}`"
    ) in readme
    assert "artifact_files_key_preview: " in readme
    assert (
        "artifact_files_key_preview_sha256: "
        f"`{artifact_bundle_summary['artifact_files_key_preview_sha256']}`"
    ) in readme
    assert (
        "artifact_files_key_tail_count: "
        f"`{artifact_bundle_summary['artifact_files_key_tail_count']}`"
    ) in readme
    assert "artifact_files_key_tail: " in readme
    assert (
        "artifact_files_key_tail_sha256: "
        f"`{artifact_bundle_summary['artifact_files_key_tail_sha256']}`"
    ) in readme
    assert (
        f"issue_artifacts_command_sha256: "
        f"`{artifact_bundle_summary['issue_artifacts_command_sha256']}`"
    ) in readme
    assert (
        f"plan_report_command_sha256: "
        f"`{artifact_bundle_summary['plan_report_command_sha256']}`"
    ) in readme
    assert (
        f"publication_visibility_key_count: "
        f"`{artifact_bundle_summary['publication_visibility_key_count']}`"
    ) in readme
    assert (
        f"publication_visibility_sha256: "
        f"`{artifact_bundle_summary['publication_visibility_sha256']}`"
    ) in readme
    assert (
        "publication_visibility_first_key: "
        f"`{artifact_bundle_summary['publication_visibility_first_key']}`"
    ) in readme
    assert (
        "publication_visibility_last_key: "
        f"`{artifact_bundle_summary['publication_visibility_last_key']}`"
    ) in readme
    assert (
        "publication_visibility_key_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_visibility_key_boundary_sha256']}`"
    ) in readme
    assert (
        "publication_visibility_key_preview_count: "
        f"`{artifact_bundle_summary['publication_visibility_key_preview_count']}`"
    ) in readme
    assert "publication_visibility_key_preview: " in readme
    assert (
        "publication_visibility_key_preview_sha256: "
        f"`{artifact_bundle_summary['publication_visibility_key_preview_sha256']}`"
    ) in readme
    assert (
        "publication_visibility_key_tail_count: "
        f"`{artifact_bundle_summary['publication_visibility_key_tail_count']}`"
    ) in readme
    assert "publication_visibility_key_tail: " in readme
    assert (
        "publication_visibility_key_tail_sha256: "
        f"`{artifact_bundle_summary['publication_visibility_key_tail_sha256']}`"
    ) in readme
    assert (
        f"publication_visibility_summary_sha256: "
        f"`{artifact_bundle_summary['publication_visibility_summary_sha256']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_key_count: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_key_count']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_sha256: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_sha256']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_first_key: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_first_key']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_last_key: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_last_key']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_key_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_key_boundary_sha256']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_key_preview_count: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_key_preview_count']}`"
    ) in readme
    assert "publication_tag_publish_decision_key_preview: " in readme
    assert (
        "publication_tag_publish_decision_key_preview_sha256: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_key_preview_sha256']}`"
    ) in readme
    assert (
        "publication_tag_publish_decision_key_tail_count: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_key_tail_count']}`"
    ) in readme
    assert "publication_tag_publish_decision_key_tail: " in readme
    assert (
        "publication_tag_publish_decision_key_tail_sha256: "
        f"`{artifact_bundle_summary['publication_tag_publish_decision_key_tail_sha256']}`"
    ) in readme
    assert "publication_tag_publish_decision_status: `blocked_by_worktree`" in readme
    assert "publication_tag_can_push: `false`" in readme
    assert (
        "publication_tag_required_action_sha256: "
        f"`{artifact_bundle_summary['publication_tag_required_action_sha256']}`"
    ) in readme
    assert "blocker_count: `2`" in readme
    assert f"blockers_sha256: `{_stable_json_sha256(plan.blockers)}`" in readme
    assert (
        "blocker_first_item: "
        f"`{artifact_bundle_summary['blocker_first_item']}`"
    ) in readme
    assert (
        "blocker_last_item: "
        f"`{artifact_bundle_summary['blocker_last_item']}`"
    ) in readme
    assert (
        "blocker_boundary_sha256: "
        f"`{artifact_bundle_summary['blocker_boundary_sha256']}`"
    ) in readme
    assert (
        "blocker_preview_count: "
        f"`{artifact_bundle_summary['blocker_preview_count']}`"
    ) in readme
    assert "blocker_preview: " in readme
    assert (
        "blocker_preview_sha256: "
        f"`{artifact_bundle_summary['blocker_preview_sha256']}`"
    ) in readme
    assert (
        "blocker_tail_count: "
        f"`{artifact_bundle_summary['blocker_tail_count']}`"
    ) in readme
    assert "blocker_tail: " in readme
    assert (
        "blocker_tail_sha256: "
        f"`{artifact_bundle_summary['blocker_tail_sha256']}`"
    ) in readme
    assert f"next_action_count: `{len(plan.next_actions)}`" in readme
    assert f"next_actions_sha256: `{_stable_json_sha256(plan.next_actions)}`" in readme
    assert (
        "next_action_first_item: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['next_action_first_item'])}"
    ) in readme
    assert (
        "next_action_last_item: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['next_action_last_item'])}"
    ) in readme
    assert (
        "next_action_boundary_sha256: "
        f"`{artifact_bundle_summary['next_action_boundary_sha256']}`"
    ) in readme
    assert (
        "next_action_preview_count: "
        f"`{artifact_bundle_summary['next_action_preview_count']}`"
    ) in readme
    assert "next_action_preview: " in readme
    assert (
        "next_action_preview_sha256: "
        f"`{artifact_bundle_summary['next_action_preview_sha256']}`"
    ) in readme
    assert (
        "next_action_tail_count: "
        f"`{artifact_bundle_summary['next_action_tail_count']}`"
    ) in readme
    assert "next_action_tail: " in readme
    assert (
        "next_action_tail_sha256: "
        f"`{artifact_bundle_summary['next_action_tail_sha256']}`"
    ) in readme
    assert "publication_next_action_count: `3`" in readme
    assert (
        f"publication_next_actions_sha256: "
        f"`{_stable_json_sha256(plan.publication_next_actions)}`"
    ) in readme
    assert (
        "publication_next_action_first_item: "
        f"{plan_next_iteration._summary_inline_code(plan.publication_next_actions[0])}"
    ) in readme
    assert (
        "publication_next_action_last_item: "
        f"{plan_next_iteration._summary_inline_code(plan.publication_next_actions[-1])}"
    ) in readme
    assert (
        "publication_next_action_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_next_action_boundary_sha256']}`"
    ) in readme
    assert (
        "publication_next_action_preview_count: "
        f"`{artifact_bundle_summary['publication_next_action_preview_count']}`"
    ) in readme
    assert (
        "publication_next_action_preview: "
        f"`{json.dumps(artifact_bundle_summary['publication_next_action_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "publication_next_action_preview_sha256: "
        f"`{artifact_bundle_summary['publication_next_action_preview_sha256']}`"
    ) in readme
    assert (
        "publication_next_action_tail_count: "
        f"`{artifact_bundle_summary['publication_next_action_tail_count']}`"
    ) in readme
    assert (
        "publication_next_action_tail: "
        f"`{json.dumps(artifact_bundle_summary['publication_next_action_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "publication_next_action_tail_sha256: "
        f"`{artifact_bundle_summary['publication_next_action_tail_sha256']}`"
    ) in readme
    assert (
        "publication_primary_next_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "publication_handoff_key_count: `29`" in readme
    assert "publication_handoff_schema_version: `1`" in readme
    assert "publication_handoff_first_key: `schema_version`" in readme
    assert "publication_handoff_last_key: `publish_script_command_sha256`" in readme
    assert (
        "publication_handoff_key_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_handoff_key_boundary_sha256']}`"
    ) in readme
    assert (
        "publication_handoff_key_preview_count: "
        f"`{artifact_bundle_summary['publication_handoff_key_preview_count']}`"
    ) in readme
    assert (
        "publication_handoff_key_preview: "
        f"`{json.dumps(artifact_bundle_summary['publication_handoff_key_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "publication_handoff_key_preview_sha256: "
        f"`{artifact_bundle_summary['publication_handoff_key_preview_sha256']}`"
    ) in readme
    assert (
        "publication_handoff_key_tail_count: "
        f"`{artifact_bundle_summary['publication_handoff_key_tail_count']}`"
    ) in readme
    assert (
        "publication_handoff_key_tail: "
        f"`{json.dumps(artifact_bundle_summary['publication_handoff_key_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "publication_handoff_key_tail_sha256: "
        f"`{artifact_bundle_summary['publication_handoff_key_tail_sha256']}`"
    ) in readme
    assert (
        f"publication_handoff_sha256: "
        f"`{artifact_bundle_summary['publication_handoff_sha256']}`"
    ) in readme
    assert "commit_cadence_status: `needs_more_commit_days`" in readme
    assert "commit_cadence_missing_commit_days: `1`" in readme
    assert (
        "commit_cadence_primary_next_action: "
        "`Ship verified slices on `1` more unique commit days this week.`"
    ) in readme
    assert (
        "publication_handoff_candidate_issue_gate_primary_reason_code: "
        "`publication_not_published`"
    ) in readme
    assert (
        "publication_handoff_candidate_issue_gate_primary_reason_description: "
        "`The latest local release branch or tag is not visible upstream.`"
    ) in readme
    assert (
        "publication_handoff_candidate_issue_gate_primary_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "commit_cadence_status: `needs_more_commit_days`" in readme
    assert "commit_cadence_commit_day_count: `2`" in readme
    assert "commit_cadence_min_commit_days: `3`" in readme
    assert "commit_cadence_missing_commit_days: `1`" in readme
    assert "commit_cadence_next_action_count: `1`" in readme
    assert (
        "commit_cadence_primary_next_action: "
        f"{plan_next_iteration._summary_inline_code('Ship verified slices on `1` more unique commit days this week.')}"
    ) in readme
    assert f"commit_cadence_commit_days_sha256: `{_stable_json_sha256([])}`" in readme
    assert (
        "commit_cadence_next_actions_sha256: "
        f"`{_stable_json_sha256(['Ship verified slices on `1` more unique commit days this week.'])}`"
    ) in readme
    assert (
        f"publication_ref_context_key_count: "
        f"`{artifact_bundle_summary['publication_ref_context_key_count']}`"
    ) in readme
    assert (
        f"publication_ref_context_sha256: "
        f"`{_stable_json_sha256(plan.publication_ref_context)}`"
    ) in readme
    assert "publication_ref_context_first_key: `repo_root`" in readme
    assert "publication_ref_context_last_key: `remote_checked`" in readme
    assert (
        "publication_ref_context_key_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_ref_context_key_boundary_sha256']}`"
    ) in readme
    assert (
        "publication_ref_context_key_preview_count: "
        f"`{artifact_bundle_summary['publication_ref_context_key_preview_count']}`"
    ) in readme
    assert (
        "publication_ref_context_key_preview: "
        f"`{json.dumps(artifact_bundle_summary['publication_ref_context_key_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "publication_ref_context_key_preview_sha256: "
        f"`{artifact_bundle_summary['publication_ref_context_key_preview_sha256']}`"
    ) in readme
    assert (
        "publication_ref_context_key_tail_count: "
        f"`{artifact_bundle_summary['publication_ref_context_key_tail_count']}`"
    ) in readme
    assert (
        "publication_ref_context_key_tail: "
        f"`{json.dumps(artifact_bundle_summary['publication_ref_context_key_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "publication_ref_context_key_tail_sha256: "
        f"`{artifact_bundle_summary['publication_ref_context_key_tail_sha256']}`"
    ) in readme
    assert (
        f"publication_publish_command_count: "
        f"`{artifact_bundle_summary['publication_publish_command_count']}`"
    ) in readme
    assert (
        f"publication_publish_commands_sha256: "
        f"`{_stable_json_sha256(plan.publication_publish_commands)}`"
    ) in readme
    assert (
        "publication_publish_first_command: "
        f"{plan_next_iteration._summary_inline_code(plan.publication_publish_commands[0])}"
    ) in readme
    assert (
        "publication_publish_last_command: "
        f"{plan_next_iteration._summary_inline_code(plan.publication_publish_commands[-1])}"
    ) in readme
    assert (
        "publication_publish_command_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_publish_command_boundary_sha256']}`"
    ) in readme
    assert (
        "publication_primary_publish_command: "
        f"`{plan.publication_publish_commands[0]}`"
    ) in readme
    assert (
        f"publication_publish_script_path_sha256: "
        f"`{artifact_bundle_summary['publication_publish_script_path_sha256']}`"
    ) in readme
    assert (
        f"publication_publish_script_command_sha256: "
        f"`{artifact_bundle_summary['publication_publish_script_command_sha256']}`"
    ) in readme
    assert f"publication_worktree_status_count: `{len(plan.publication_worktree_status)}`" in readme
    assert (
        f"publication_worktree_status_sha256: "
        f"`{_stable_json_sha256(plan.publication_worktree_status)}`"
    ) in readme
    assert (
        "publication_worktree_status_first_item: "
        f"{plan_next_iteration._summary_inline_code(plan.publication_worktree_status[0])}"
    ) in readme
    assert (
        "publication_worktree_status_last_item: "
        f"{plan_next_iteration._summary_inline_code(plan.publication_worktree_status[-1])}"
    ) in readme
    assert (
        "publication_worktree_status_boundary_sha256: "
        f"`{artifact_bundle_summary['publication_worktree_status_boundary_sha256']}`"
    ) in readme
    assert "release_draft_handoff_key_count: `19`" in readme
    assert "release_draft_handoff_schema_version: `1`" in readme
    assert "release_draft_handoff_primary_issue: `release draft is missing`" in readme
    assert (
        "release_draft_handoff_primary_required_action: "
        "`Resolve release draft issue: release draft is missing`"
    ) in readme
    assert "release_draft_handoff_first_key: `schema_version`" in readme
    assert "release_draft_handoff_last_key: `target_version`" in readme
    assert (
        "release_draft_handoff_key_boundary_sha256: "
        f"`{artifact_bundle_summary['release_draft_handoff_key_boundary_sha256']}`"
    ) in readme
    assert (
        "release_draft_handoff_key_preview_count: "
        f"`{artifact_bundle_summary['release_draft_handoff_key_preview_count']}`"
    ) in readme
    assert (
        "release_draft_handoff_key_preview: "
        f"`{json.dumps(artifact_bundle_summary['release_draft_handoff_key_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "release_draft_handoff_key_preview_sha256: "
        f"`{artifact_bundle_summary['release_draft_handoff_key_preview_sha256']}`"
    ) in readme
    assert (
        "release_draft_handoff_key_tail_count: "
        f"`{artifact_bundle_summary['release_draft_handoff_key_tail_count']}`"
    ) in readme
    assert (
        "release_draft_handoff_key_tail: "
        f"`{json.dumps(artifact_bundle_summary['release_draft_handoff_key_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "release_draft_handoff_key_tail_sha256: "
        f"`{artifact_bundle_summary['release_draft_handoff_key_tail_sha256']}`"
    ) in readme
    assert (
        f"release_draft_handoff_sha256: "
        f"`{artifact_bundle_summary['release_draft_handoff_sha256']}`"
    ) in readme
    assert f"release_draft_path: `{plan.release_draft_path}`" in readme
    assert (
        f"release_draft_path_sha256: "
        f"`{artifact_bundle_summary['release_draft_path_sha256']}`"
    ) in readme
    assert "release_draft_primary_issue: `release draft is missing`" in readme
    assert "primary_issue: `release draft is missing`" in readme
    assert (
        f"release_draft_required_action_count: "
        f"`{artifact_bundle_summary['release_draft_required_action_count']}`"
    ) in readme
    assert (
        f"release_draft_required_actions_sha256: "
        f"`{artifact_bundle_summary['release_draft_required_actions_sha256']}`"
    ) in readme
    assert (
        "release_draft_first_required_action: "
        "`Resolve release draft issue: release draft is missing`"
    ) in readme
    assert (
        "release_draft_last_required_action: "
        "`Resolve release draft issue: release draft missing snippet: ## 发版前验证`"
    ) in readme
    assert (
        "release_draft_required_action_boundary_sha256: "
        f"`{artifact_bundle_summary['release_draft_required_action_boundary_sha256']}`"
    ) in readme
    assert (
        "release_draft_required_action_preview_count: "
        f"`{artifact_bundle_summary['release_draft_required_action_preview_count']}`"
    ) in readme
    assert (
        "release_draft_required_action_preview: "
        f"`{json.dumps(artifact_bundle_summary['release_draft_required_action_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "release_draft_required_action_preview_sha256: "
        f"`{artifact_bundle_summary['release_draft_required_action_preview_sha256']}`"
    ) in readme
    assert (
        "release_draft_required_action_tail_count: "
        f"`{artifact_bundle_summary['release_draft_required_action_tail_count']}`"
    ) in readme
    assert (
        "release_draft_required_action_tail: "
        f"`{json.dumps(artifact_bundle_summary['release_draft_required_action_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "release_draft_required_action_tail_sha256: "
        f"`{artifact_bundle_summary['release_draft_required_action_tail_sha256']}`"
    ) in readme
    assert (
        "release_draft_primary_required_action: "
        "`Resolve release draft issue: release draft is missing`"
    ) in readme
    assert (
        "primary_required_action: "
        "`Resolve release draft issue: release draft is missing`"
    ) in readme
    assert (
        f"release_draft_issues_sha256: "
        f"`{artifact_bundle_summary['release_draft_issues_sha256']}`"
    ) in readme
    assert "release_draft_first_issue: `release draft is missing`" in readme
    assert (
        "release_draft_last_issue: "
        "`release draft missing snippet: ## 发版前验证`"
    ) in readme
    assert (
        "release_draft_issue_boundary_sha256: "
        f"`{artifact_bundle_summary['release_draft_issue_boundary_sha256']}`"
    ) in readme
    assert (
        "release_draft_issue_preview_count: "
        f"`{artifact_bundle_summary['release_draft_issue_preview_count']}`"
    ) in readme
    assert (
        "release_draft_issue_preview: "
        f"`{json.dumps(artifact_bundle_summary['release_draft_issue_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "release_draft_issue_preview_sha256: "
        f"`{artifact_bundle_summary['release_draft_issue_preview_sha256']}`"
    ) in readme
    assert (
        "release_draft_issue_tail_count: "
        f"`{artifact_bundle_summary['release_draft_issue_tail_count']}`"
    ) in readme
    assert (
        "release_draft_issue_tail: "
        f"`{json.dumps(artifact_bundle_summary['release_draft_issue_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "release_draft_issue_tail_sha256: "
        f"`{artifact_bundle_summary['release_draft_issue_tail_sha256']}`"
    ) in readme
    assert "validation_command_count: `6`" in readme
    assert (
        "validation_commands_sha256: "
        f"`{artifact_bundle_summary['validation_commands_sha256']}`"
    ) in readme
    assert (
        "validation_first_command: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['validation_first_command'])}"
    ) in readme
    assert (
        "validation_last_command: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['validation_last_command'])}"
    ) in readme
    assert (
        "validation_command_boundary_sha256: "
        f"`{artifact_bundle_summary['validation_command_boundary_sha256']}`"
    ) in readme
    assert (
        "validation_command_preview_count: "
        f"`{artifact_bundle_summary['validation_command_preview_count']}`"
    ) in readme
    assert (
        "validation_command_preview: "
        f"`{json.dumps(artifact_bundle_summary['validation_command_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "validation_command_preview_sha256: "
        f"`{artifact_bundle_summary['validation_command_preview_sha256']}`"
    ) in readme
    assert (
        "validation_command_tail_count: "
        f"`{artifact_bundle_summary['validation_command_tail_count']}`"
    ) in readme
    assert (
        "validation_command_tail: "
        f"`{json.dumps(artifact_bundle_summary['validation_command_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "validation_command_tail_sha256: "
        f"`{artifact_bundle_summary['validation_command_tail_sha256']}`"
    ) in readme
    assert "review_checklist_count: `7`" in readme
    assert (
        "review_checklist_sha256: "
        f"`{artifact_bundle_summary['review_checklist_sha256']}`"
    ) in readme
    assert (
        "review_checklist_first_item: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['review_checklist_first_item'])}"
    ) in readme
    assert (
        "review_checklist_last_item: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['review_checklist_last_item'])}"
    ) in readme
    assert (
        "review_checklist_boundary_sha256: "
        f"`{artifact_bundle_summary['review_checklist_boundary_sha256']}`"
    ) in readme
    assert (
        "review_checklist_preview_count: "
        f"`{artifact_bundle_summary['review_checklist_preview_count']}`"
    ) in readme
    assert (
        "review_checklist_preview: "
        f"`{json.dumps(artifact_bundle_summary['review_checklist_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "review_checklist_preview_sha256: "
        f"`{artifact_bundle_summary['review_checklist_preview_sha256']}`"
    ) in readme
    assert (
        "review_checklist_tail_count: "
        f"`{artifact_bundle_summary['review_checklist_tail_count']}`"
    ) in readme
    assert (
        "review_checklist_tail: "
        f"`{json.dumps(artifact_bundle_summary['review_checklist_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "review_checklist_tail_sha256: "
        f"`{artifact_bundle_summary['review_checklist_tail_sha256']}`"
    ) in readme
    assert "create_issues_safety_contract_key_count: `5`" in readme
    assert (
        "create_issues_safety_contract_sha256: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_sha256']}`"
    ) in readme
    assert "create_issues_safety_contract_first_key: `dry_run_supported`" in readme
    assert "create_issues_safety_contract_last_key: `preflight_json`" in readme
    assert (
        "create_issues_safety_contract_key_boundary_sha256: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_key_boundary_sha256']}`"
    ) in readme
    assert (
        "create_issues_safety_contract_key_preview_count: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_key_preview_count']}`"
    ) in readme
    assert (
        "create_issues_safety_contract_key_preview: "
        f"`{json.dumps(artifact_bundle_summary['create_issues_safety_contract_key_preview'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "create_issues_safety_contract_key_preview_sha256: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_key_preview_sha256']}`"
    ) in readme
    assert (
        "create_issues_safety_contract_key_tail_count: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_key_tail_count']}`"
    ) in readme
    assert (
        "create_issues_safety_contract_key_tail: "
        f"`{json.dumps(artifact_bundle_summary['create_issues_safety_contract_key_tail'], ensure_ascii=False)}`"
    ) in readme
    assert (
        "create_issues_safety_contract_key_tail_sha256: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_key_tail_sha256']}`"
    ) in readme
    assert "publication_ok: `false`" in readme
    assert "publication_visibility_status: `dirty_worktree`" in readme
    assert "publication_branch: `master`" in readme
    assert "publication_upstream: `origin/master`" in readme
    assert "publication_remote: `origin`" in readme
    assert "publication_latest_tag: `v0.16.1`" in readme
    assert "publication_tag_commit: `abc123`" in readme
    assert "publication_local_head: `abc123`" in readme
    assert "publication_upstream_head: `def456`" in readme
    assert "publication_tag_points_at_head: `true`" in readme
    assert "publication_tag_commit_in_upstream: `false`" in readme
    assert "publication_branch_published: `false`" in readme
    assert "publication_tag_published: `false`" in readme
    assert "publication_remote_branch_head: `None`" in readme
    assert "publication_remote_tag_commit: `None`" in readme
    assert "publication_remote_checked: `false`" in readme
    assert "publication_ahead_count: `2`" in readme
    assert "publication_behind_count: `0`" in readme
    assert "release_draft_ok: `false`" in readme
    assert "release_draft_issue_count: `2`" in readme
    assert f"candidate_issue_gate_key_count: `{len(_blocked_candidate_issue_gate())}`" in readme
    assert (
        f"candidate_issue_gate_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_sha256']}`"
    ) in readme
    assert "candidate_issue_gate_status: `blocked_by_publication`" in readme
    assert "can_create_issues: `false`" in readme
    assert "requires_maintainer_review: `true`" in readme
    assert (
        f"candidate_issue_gate_summary_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_summary_sha256']}`"
    ) in readme
    assert "candidate_issue_gate_evidence_key_count: `13`" in readme
    assert (
        f"candidate_issue_gate_evidence_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_evidence_sha256']}`"
    ) in readme
    assert (
        "candidate_issue_gate_evidence_first_key: "
        f"`{artifact_bundle_summary['candidate_issue_gate_evidence_first_key']}`"
    ) in readme
    assert (
        "candidate_issue_gate_evidence_last_key: "
        f"`{artifact_bundle_summary['candidate_issue_gate_evidence_last_key']}`"
    ) in readme
    assert (
        "candidate_issue_gate_evidence_key_boundary_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_evidence_key_boundary_sha256']}`"
    ) in readme
    assert "candidate_issue_gate_reason_description_count: `3`" in readme
    assert (
        f"candidate_issue_gate_reason_descriptions_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_reason_descriptions_sha256']}`"
    ) in readme
    assert "candidate_issue_gate_reason_code_count: `3`" in readme
    assert (
        f"candidate_issue_gate_reason_codes_sha256: "
        f"`{_blocked_candidate_issue_gate()['reason_codes_sha256']}`"
    ) in readme
    assert "candidate_issue_gate_first_reason_code: `publication_not_published`" in readme
    assert "candidate_issue_gate_last_reason_code: `release_draft_issues`" in readme
    assert (
        "candidate_issue_gate_reason_code_boundary_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_reason_code_boundary_sha256']}`"
    ) in readme
    assert "candidate_issue_gate_primary_reason_code: `publication_not_published`" in readme
    assert (
        "candidate_issue_gate_primary_reason_description: "
        "`The latest local release branch or tag is not visible upstream.`"
    ) in readme
    assert "candidate_issue_gate_required_action_count: `5`" in readme
    assert (
        f"candidate_issue_gate_required_actions_sha256: "
        f"`{_blocked_candidate_issue_gate()['required_actions_sha256']}`"
    ) in readme
    assert (
        "candidate_issue_gate_first_required_action: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['candidate_issue_gate_first_required_action'])}"
    ) in readme
    assert (
        "candidate_issue_gate_last_required_action: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['candidate_issue_gate_last_required_action'])}"
    ) in readme
    assert (
        "candidate_issue_gate_required_action_boundary_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_required_action_boundary_sha256']}`"
    ) in readme
    assert (
        "candidate_issue_gate_primary_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "## Candidate Issue Gate Quick Summary" in readme
    assert readme.index("## Candidate Issue Gate Quick Summary") < readme.index("## Artifact Bundle Summary")
    assert "## Commit Cadence" in readme
    assert readme.index("## Candidate Issue Gate Quick Summary") < readme.index("## Commit Cadence")
    assert readme.index("## Commit Cadence") < readme.index("## Artifact Bundle Summary")
    assert "- summary: `2/3 commit days; 1 more unique day(s) needed.`" in readme
    assert "- commit_day_count: `2`" in readme
    assert "- min_commit_days: `3`" in readme
    assert "- missing_commit_days: `1`" in readme
    assert "- commit_days: `(none)`" in readme
    assert (
        "- primary_next_action: "
        f"{plan_next_iteration._summary_inline_code('Ship verified slices on `1` more unique commit days this week.')}"
    ) in readme
    assert "### Commit Cadence Next Actions" in readme
    assert "- Ship verified slices on `1` more unique commit days this week." in readme
    assert "- status: `blocked_by_publication`" in readme
    assert "- can_create_issues: `false`" in readme
    assert "- requires_maintainer_review: `true`" in readme
    assert "- publication_ok: `false`" in readme
    assert "- release_draft_ok: `false`" in readme
    assert "- blocker_count: `2`" in readme
    assert f"- next_action_count: `{len(plan.next_actions)}`" in readme
    assert "- publication_next_action_count: `3`" in readme
    assert "- publication_publish_command_count: `1`" in readme
    assert "- publication_publish_script_path: `/tmp/cliany-publish-release.sh`" in readme
    assert (
        f"- publication_publish_script_path_sha256: "
        f"`{_stable_json_sha256('/tmp/cliany-publish-release.sh')}`"
    ) in readme
    assert (
        "- publication_publish_script_command: "
        "`python scripts/check_release_publication.py --json --publish-script /tmp/cliany-publish-release.sh`"
    ) in readme
    publish_script_command = (
        "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    )
    assert (
        f"- publication_publish_script_command_sha256: "
        f"`{_stable_json_sha256(publish_script_command)}`"
    ) in readme
    assert "- reason_code_count: `3`" in readme
    assert "- required_action_count: `5`" in readme
    assert "- primary_reason_code: `publication_not_published`" in readme
    assert (
        "- primary_reason_description: "
        "`The latest local release branch or tag is not visible upstream.`"
    ) in readme
    assert (
        "- primary_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "- latest_tag: `v0.16.1`" in readme
    assert "- publication_branch: `master`" in readme
    assert "- publication_upstream: `origin/master`" in readme
    assert "- publication_remote: `origin`" in readme
    assert "- publication_local_head: `abc123`" in readme
    assert "- publication_tag_commit: `abc123`" in readme
    assert "- publication_upstream_head: `def456`" in readme
    assert "- publication_tag_points_at_head: `true`" in readme
    assert "- publication_tag_commit_in_upstream: `false`" in readme
    assert "- publication_branch_published: `false`" in readme
    assert "- publication_tag_published: `false`" in readme
    assert "- publication_remote_branch_head: `(none)`" in readme
    assert "- publication_remote_tag_commit: `(none)`" in readme
    assert "- publication_worktree_clean: `false`" in readme
    assert "- publication_ahead_count: `2`" in readme
    assert "- publication_behind_count: `0`" in readme
    assert "- publication_remote_checked: `false`" in readme
    assert "- release_draft_issue_count: `2`" in readme
    assert "- release_draft_path: `docs/releases/v0.16.2-draft.md`" in readme
    assert "- visibility: `dirty_worktree`" in readme
    assert (
        "- visibility_summary: "
        "`Worktree has uncommitted changes; resolve them before publishing release refs.`"
    ) in readme
    assert "- tag_publish_decision: `blocked_by_worktree`" in readme
    assert "- tag_can_push: `false`" in readme
    assert (
        "- tag_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "dry_run_supported: `true`" in readme
    assert "preflight_required: `true`" in readme
    assert "## Publication Handoff" in readme
    assert "schema_version: `1`" in readme
    assert "publication_ok: `false`" in readme
    assert "candidate_issue_gate: `blocked_by_publication`" in readme
    assert "can_create_issues: `false`" in readme
    assert "gate_summary: Do not create candidate issues until the latest local release is publicly visible." in readme
    assert "gate_reason_code_count: `3`" in readme
    assert f"gate_reason_codes_sha256: `{_blocked_candidate_issue_gate()['reason_codes_sha256']}`" in readme
    assert "gate_required_action_count: `5`" in readme
    assert f"gate_required_actions_sha256: `{_blocked_candidate_issue_gate()['required_actions_sha256']}`" in readme
    assert "gate_primary_reason_code: `publication_not_published`" in readme
    assert (
        "gate_primary_reason_description: "
        "`The latest local release branch or tag is not visible upstream.`"
    ) in readme
    assert (
        "gate_primary_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "gate_reason_codes: `publication_not_published`, `dirty_worktree`, `release_draft_issues`" in readme
    assert "gate_reason_descriptions:" in readme
    assert "`publication_not_published`: The latest local release branch or tag is not visible upstream." in readme
    assert "`dirty_worktree`: The working tree has uncommitted changes that must be resolved first." in readme
    assert "`release_draft_issues`: The target release draft still has validation issues." in readme
    assert "gate_evidence_latest_tag: `v0.16.1`" in readme
    assert "gate_evidence_ahead_count: `2`" in readme
    assert "gate_evidence_worktree_clean: `false`" in readme
    assert "gate_evidence_tag_decision: `blocked_by_worktree`" in readme
    assert "gate_evidence_tag_can_push: `false`" in readme
    assert (
        "gate_evidence_tag_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "gate_evidence_release_draft_ok: `false`" in readme
    assert "gate_evidence_release_draft_issues: `2`" in readme
    assert "visibility: `dirty_worktree`" in readme
    assert (
        "visibility_summary: Worktree has uncommitted changes; "
        "resolve them before publishing release refs."
    ) in readme
    assert "tag_publish_decision: `blocked_by_worktree`" in readme
    assert "tag_can_push: `false`" in readme
    assert (
        "tag_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert (
        "plan_report_command: "
        "`python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--report /tmp/cliany-next-iteration.md`"
    ) in readme
    assert (
        f"plan_report_command_sha256: "
        f"`{_stable_json_sha256(plan.plan_report_command)}`"
    ) in readme
    assert (
        "issue_artifacts_command: "
        "`python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--issues-dir /tmp/cliany-candidate-issues`"
    ) in readme
    assert (
        f"issue_artifacts_command_sha256: "
        f"`{_stable_json_sha256(plan.issue_artifacts_command)}`"
    ) in readme
    assert "latest_tag: `v0.16.1`" in readme
    assert "local_head: `abc123`" in readme
    assert "worktree_clean: `false`" in readme
    assert (
        "primary_next_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "publish_command_count: `1`" in readme
    assert "primary_publish_command: `python scripts/check_release_publication.py --json`" in readme
    assert "publish_script_path: `/tmp/cliany-publish-release.sh`" in readme
    assert (
        f"publish_script_path_sha256: "
        f"`{_stable_json_sha256('/tmp/cliany-publish-release.sh')}`"
    ) in readme
    publish_script_command = (
        "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    )
    assert (
        f"publish_script_command_sha256: "
        f"`{_stable_json_sha256(publish_script_command)}`"
    ) in readme
    assert "### Publication Next Actions" in readme
    assert "Commit, stash, or discard local worktree changes" in readme
    assert "Push `master` to `origin`; local branch is ahead by `2` commits." in readme
    assert "Push tag `v0.16.1` after the branch is published." in readme
    assert "### Publication Publish Script" in readme
    assert "- path: `/tmp/cliany-publish-release.sh`" in readme
    assert (
        "python scripts/check_release_publication.py --json "
        "--publish-script /tmp/cliany-publish-release.sh"
    ) in readme
    assert "python scripts/check_release_publication.py --json" in readme
    assert "## Release Draft Handoff" in readme
    assert "schema_version: `1`" in readme
    assert "release_draft_ok: `false`" in readme
    assert "release_draft_path: `docs/releases/v0.16.2-draft.md`" in readme
    assert (
        f"release_draft_path_sha256: "
        f"`{_stable_json_sha256('docs/releases/v0.16.2-draft.md')}`"
    ) in readme
    assert "release_draft_issue_count: `2`" in readme
    assert "release_draft_primary_issue: `release draft is missing`" in readme
    assert "primary_issue: `release draft is missing`" in readme
    assert (
        "release_draft_primary_required_action: "
        "`Resolve release draft issue: release draft is missing`"
    ) in readme
    assert (
        "primary_required_action: "
        "`Resolve release draft issue: release draft is missing`"
    ) in readme
    assert "release_draft_required_action_count: `2`" in readme
    assert (
        f"release_draft_required_actions_sha256: "
        f"`{_stable_json_sha256(expected_release_draft_handoff['release_draft_required_actions'])}`"
    ) in readme
    assert "release_draft_required_actions:" in readme
    assert "- Resolve release draft issue: release draft is missing" in readme
    assert "- Resolve release draft issue: release draft missing snippet: ## 发版前验证" in readme
    assert (
        f"release_draft_issues_sha256: "
        f"`{_stable_json_sha256(plan.release_draft_issues)}`"
    ) in readme
    assert "- release draft is missing" in readme
    assert "- release draft missing snippet: ## 发版前验证" in readme
    assert (
        "plan_report_command: "
        "`python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--report /tmp/cliany-next-iteration.md`"
    ) in readme
    assert (
        f"plan_report_command_sha256: "
        f"`{_stable_json_sha256(plan.plan_report_command)}`"
    ) in readme
    assert (
        "issue_artifacts_command: "
        "`python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--issues-dir /tmp/cliany-candidate-issues`"
    ) in readme
    assert (
        f"issue_artifacts_command_sha256: "
        f"`{_stable_json_sha256(plan.issue_artifacts_command)}`"
    ) in readme
    assert "Confirm release draft issues are resolved or intentionally deferred" in readme
    assert "Confirm Publication Next Actions are resolved or intentionally deferred" in readme
    assert "before running create-issues.sh" in readme
    assert "expected target URL, candidate commands" in readme
    assert (
        "offline validation commands, candidate_package_validation_command, "
        "and promotion_command_plan for each case"
        in readme
    )
    assert "release publication preflight" in readme
    assert "python scripts/check_release_publication.py --strict --json" in readme
    assert "/tmp/cliany-issue-publication-check.json" in readme
    assert "prints that JSON before exiting" in readme
    assert "### Create Issues Safety" in readme
    assert "dry_run_supported: `true`" in readme
    assert "dry_run_env: `CLIANY_CREATE_ISSUES_DRY_RUN=1`" in readme
    assert "dry_run_command: `CLIANY_CREATE_ISSUES_DRY_RUN=1 create-issues.sh`" in readme
    assert "preflight_required: `true`" in readme
    assert "preflight_command: `python scripts/check_release_publication.py --strict --json`" in readme
    assert "preflight_json: `/tmp/cliany-issue-publication-check.json`" in readme
    assert "`create-issues.sh` is generated for review. It is not executed" in readme
    assert (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--issues-dir /tmp/cliany-candidate-issues"
    ) in readme
    assert (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--report /tmp/cliany-next-iteration.md"
    ) in readme
    assert "CLIANY_CREATE_ISSUES_DRY_RUN=1 ./create-issues.sh" in readme
    assert "python scripts/plan_next_iteration.py --target-version 0.16.2 --json" in readme
    assert "python scripts/release_readiness.py --target-version 0.16.2 --json" in readme
    assert "python scripts/check_release_publication.py --json" in readme
    assert "python scripts/validate_cases.py --strict" in readme


def test_plan_cli_writes_json_for_current_repo(capsys):
    exit_code = plan_next_iteration.main(["--json", "--target-version", "0.16.2"])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["target_version"] == "0.16.2"
    assert "recommended_theme" in payload
    assert "case_promotion_evidence_summary" in payload
    assert "next_actions" in payload
