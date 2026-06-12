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
        "reason_descriptions": {
            "publication_not_published": "The latest local release branch or tag is not visible upstream.",
            "dirty_worktree": "The working tree has uncommitted changes that must be resolved first.",
            "release_draft_issues": "The target release draft still has validation issues.",
        },
        "required_action_count": len(required_actions),
        "required_actions_sha256": _stable_json_sha256(required_actions),
        "required_actions": required_actions,
        "evidence": {
            "publication_ok": False,
            "publication_visibility_status": "dirty_worktree",
            "publication_worktree_clean": False,
            "publication_remote_checked": False,
            "publication_branch": "master",
            "publication_latest_tag": "v0.16.1",
            "publication_ahead_count": 2,
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
    assert plan.candidate_promotions[0].case_id == "pypi-project-search"


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
        "reason_descriptions": {
            "release_draft_issues": "The target release draft still has validation issues.",
        },
        "required_action_count": len(required_actions),
        "required_actions_sha256": _stable_json_sha256(required_actions),
        "required_actions": required_actions,
        "evidence": {
            "publication_ok": True,
            "publication_visibility_status": "published",
            "publication_worktree_clean": True,
            "publication_remote_checked": True,
            "publication_branch": "master",
            "publication_latest_tag": "v0.16.1",
            "publication_ahead_count": 0,
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
    assert data["candidate_issue_gate"] == _blocked_candidate_issue_gate()
    assert not str(data["candidate_issue_gate"]["evidence"]["release_draft_path"]).startswith("/")
    assert data["publication_publish_commands"] == [
        "python scripts/check_release_publication.py --json",
    ]
    assert data["publication_publish_command_count"] == 1
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
    assert "| publication_next_action_count | `3` |" in text
    assert "| publication_publish_command_count | `1` |" in text
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
    assert "candidate_issue_gate:" in text
    assert "publication_next_action_count: 3" in text
    assert "publication_publish_command_count: 1" in text
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
    stable_issue_metadata = [
        {
            "case_id": item["case_id"],
            "issue_title": item["issue_title"],
            "issue_labels": item["issue_labels"],
            "target_url": item["target_url"],
            "commands": item["commands"],
            "offline_commands": item["offline_commands"],
            "issue_body_name": item["issue_body_name"],
        }
        for item in metadata
    ]
    issue_metadata_summary = {
        "metadata_count": len(stable_issue_metadata),
        "metadata_sha256": _stable_json_sha256(stable_issue_metadata),
    }
    expected_release_draft_handoff = {
        "release_draft_ok": False,
        "release_draft_issue_count": 2,
        "release_draft_path": "docs/releases/v0.16.2-draft.md",
        "release_draft_path_sha256": _stable_json_sha256("docs/releases/v0.16.2-draft.md"),
        "release_draft_issues": [
            "release draft is missing",
            "release draft missing snippet: ## 发版前验证",
        ],
        "target_version": "0.16.2",
    }
    expected_publication_handoff = {
        "publication_ok": False,
        "candidate_issue_gate": _blocked_candidate_issue_gate(),
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
    expected_artifact_files = {
        "readme": "README.md",
        "issue_metadata": "issue-metadata.json",
        "publication_handoff": "publication-handoff.json",
        "release_draft_handoff": "release-draft-handoff.json",
        "create_issues_script": "create-issues.sh",
        "issue_bodies": ["pypi-project-search.md", "npm-package-search.md"],
    }
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
    candidate_issue_gate_evidence = _blocked_candidate_issue_gate()["evidence"]
    candidate_issue_gate_reason_descriptions = _blocked_candidate_issue_gate()["reason_descriptions"]
    artifact_bundle_summary = {
        "target_version": "0.16.2",
        "candidate_count": 2,
        "candidate_cases_sha256": _stable_json_sha256(["pypi-project-search", "npm-package-search"]),
        "body_count": 2,
        "issue_body_summary_sha256": _stable_json_sha256(issue_body_summary),
        "review_item_count": len(review_order),
        "review_order_sha256": review_order_sha256,
        "inventory_sha256": issue_body_summary["inventory_sha256"],
        "issue_metadata_count": issue_metadata_summary["metadata_count"],
        "issue_metadata_sha256": issue_metadata_summary["metadata_sha256"],
        "artifact_files_key_count": len(expected_artifact_files),
        "artifact_files_sha256": _stable_json_sha256(expected_artifact_files),
        "issue_artifacts_command_sha256": _stable_json_sha256(plan.issue_artifacts_command),
        "publication_visibility_key_count": len(plan.publication_visibility),
        "publication_visibility_sha256": _stable_json_sha256(plan.publication_visibility),
        "publication_visibility_summary_sha256": _stable_json_sha256(
            plan.publication_visibility["summary"]
        ),
        "blocker_count": 2,
        "blockers_sha256": _stable_json_sha256(plan.blockers),
        "next_action_count": len(plan.next_actions),
        "next_actions_sha256": _stable_json_sha256(plan.next_actions),
        "publication_next_action_count": 3,
        "publication_next_actions_sha256": _stable_json_sha256(plan.publication_next_actions),
        "publication_handoff_key_count": len(expected_publication_handoff),
        "publication_handoff_sha256": _stable_json_sha256(expected_publication_handoff),
        "publication_ref_context_key_count": len(plan.publication_ref_context),
        "publication_ref_context_sha256": _stable_json_sha256(plan.publication_ref_context),
        "publication_publish_command_count": plan.publication_publish_command_count,
        "publication_publish_commands_sha256": _stable_json_sha256(plan.publication_publish_commands),
        "publication_publish_script_path_sha256": _stable_json_sha256(
            plan.publication_publish_script_path
        ),
        "publication_publish_script_command_sha256": _stable_json_sha256(
            plan.publication_publish_script_command
        ),
        "publication_worktree_status_count": len(plan.publication_worktree_status),
        "publication_worktree_status_sha256": _stable_json_sha256(plan.publication_worktree_status),
        "release_draft_handoff_key_count": len(expected_release_draft_handoff),
        "release_draft_handoff_sha256": _stable_json_sha256(expected_release_draft_handoff),
        "release_draft_path": plan.release_draft_path,
        "release_draft_path_sha256": _stable_json_sha256(plan.release_draft_path),
        "release_draft_issues_sha256": _stable_json_sha256(plan.release_draft_issues),
        "validation_command_count": 5,
        "validation_commands_sha256": _stable_json_sha256(
            [
                (
                    "python scripts/plan_next_iteration.py --target-version 0.16.2 "
                    "--issues-dir /tmp/cliany-candidate-issues"
                ),
                "python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
                "python scripts/release_readiness.py --target-version 0.16.2 --json",
                "python scripts/check_release_publication.py --json",
                "python scripts/validate_cases.py --strict",
            ]
        ),
        "review_checklist_count": 7,
        "review_checklist_sha256": _stable_json_sha256(
            [
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
                    "and offline validation commands for each case."
                ),
                "Review each body file for scope, tasks, validation evidence, and non-goals.",
                (
                    "Keep cases as candidate until adapter package, metadata validation, "
                    "and online smoke evidence are complete."
                ),
                "Do not use real LLM keys or write runtime state into the repository.",
            ]
        ),
        "create_issues_safety_contract_key_count": 5,
        "create_issues_safety_contract_sha256": _stable_json_sha256(
            {
                "dry_run_supported": True,
                "dry_run_env": "CLIANY_CREATE_ISSUES_DRY_RUN=1",
                "preflight_required": True,
                "preflight_command": "python scripts/check_release_publication.py --strict --json",
                "preflight_json": "/tmp/cliany-issue-publication-check.json",
            }
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
        "candidate_issue_gate_reason_description_count": len(candidate_issue_gate_reason_descriptions),
        "candidate_issue_gate_reason_descriptions_sha256": _stable_json_sha256(
            candidate_issue_gate_reason_descriptions
        ),
        "candidate_issue_gate_reason_code_count": _blocked_candidate_issue_gate()["reason_code_count"],
        "candidate_issue_gate_reason_codes_sha256": _blocked_candidate_issue_gate()["reason_codes_sha256"],
        "candidate_issue_gate_primary_reason_code": "publication_not_published",
        "candidate_issue_gate_primary_reason_description": (
            "The latest local release branch or tag is not visible upstream."
        ),
        "candidate_issue_gate_required_action_count": _blocked_candidate_issue_gate()["required_action_count"],
        "candidate_issue_gate_required_actions_sha256": _blocked_candidate_issue_gate()["required_actions_sha256"],
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
    assert artifact_manifest == {
        "schema_version": 1,
        "target_version": "0.16.2",
        "artifact_bundle_summary": artifact_bundle_summary,
        "candidate_count": 2,
        "candidate_cases": ["pypi-project-search", "npm-package-search"],
        "blockers": ["release draft validation failed", "latest local release is not published"],
        "next_actions": plan.next_actions,
        "candidate_issue_gate": _blocked_candidate_issue_gate(),
        "publication_ok": False,
        "publication_visibility": {
            "status": "dirty_worktree",
            "summary": "Worktree has uncommitted changes; resolve them before publishing release refs.",
        },
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
        "create_issues_dry_run_command": f"CLIANY_CREATE_ISSUES_DRY_RUN=1 {issues_dir / 'create-issues.sh'}",
        "create_issues_safety": {
            "script": str(issues_dir / "create-issues.sh"),
            "dry_run_supported": True,
            "dry_run_env": "CLIANY_CREATE_ISSUES_DRY_RUN=1",
            "dry_run_command": f"CLIANY_CREATE_ISSUES_DRY_RUN=1 {issues_dir / 'create-issues.sh'}",
            "preflight_required": True,
            "preflight_command": "python scripts/check_release_publication.py --strict --json",
            "preflight_json": "/tmp/cliany-issue-publication-check.json",
        },
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
                "and offline validation commands for each case."
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
            "python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
            "python scripts/release_readiness.py --target-version 0.16.2 --json",
            "python scripts/check_release_publication.py --json",
            "python scripts/validate_cases.py --strict",
        ],
    }
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
    assert "`artifact-manifest.json`: schema version, candidate cases, blockers, next actions" in readme
    assert "review checklist, candidate issue gate, publication status" in readme
    assert "release draft" in readme
    assert "handoff, reproduction" in readme
    assert "body file name" in readme
    assert "`publication-handoff.json`: publication status, candidate issue gate, visibility" in readme
    assert "`release-draft-handoff.json`: target version, release draft ok status" in readme
    assert "## Candidate Summary" in readme
    assert "| Case | Issue Body | Target URL | Candidate Commands | Offline Validation Commands |" in readme
    assert (
        "| `pypi-project-search` | `pypi-project-search.md` | "
        "https://pypi.org/search/?q=cliany-site | 2 | 2 |"
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
    assert "target_version: `0.16.2`" in readme
    assert "candidate_count: `2`" in readme
    assert "candidate_cases_sha256: `" in readme
    assert f"candidate_cases_sha256: `{artifact_bundle_summary['candidate_cases_sha256']}`" in readme
    assert f"issue_body_summary_sha256: `{artifact_bundle_summary['issue_body_summary_sha256']}`" in readme
    assert "review_item_count: `7`" in readme
    assert f"review_order_sha256: `{review_order_sha256}`" in readme
    assert f"issue_metadata_count: `{issue_metadata_summary['metadata_count']}`" in readme
    assert f"issue_metadata_sha256: `{issue_metadata_summary['metadata_sha256']}`" in readme
    assert "artifact_files_key_count: `6`" in readme
    assert f"artifact_files_sha256: `{artifact_bundle_summary['artifact_files_sha256']}`" in readme
    assert (
        f"issue_artifacts_command_sha256: "
        f"`{artifact_bundle_summary['issue_artifacts_command_sha256']}`"
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
        f"publication_visibility_summary_sha256: "
        f"`{artifact_bundle_summary['publication_visibility_summary_sha256']}`"
    ) in readme
    assert "blocker_count: `2`" in readme
    assert f"blockers_sha256: `{_stable_json_sha256(plan.blockers)}`" in readme
    assert f"next_action_count: `{len(plan.next_actions)}`" in readme
    assert f"next_actions_sha256: `{_stable_json_sha256(plan.next_actions)}`" in readme
    assert "publication_next_action_count: `3`" in readme
    assert (
        f"publication_next_actions_sha256: "
        f"`{_stable_json_sha256(plan.publication_next_actions)}`"
    ) in readme
    assert "publication_handoff_key_count: `14`" in readme
    assert (
        f"publication_handoff_sha256: "
        f"`{artifact_bundle_summary['publication_handoff_sha256']}`"
    ) in readme
    assert (
        f"publication_ref_context_key_count: "
        f"`{artifact_bundle_summary['publication_ref_context_key_count']}`"
    ) in readme
    assert (
        f"publication_ref_context_sha256: "
        f"`{_stable_json_sha256(plan.publication_ref_context)}`"
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
    assert "release_draft_handoff_key_count: `6`" in readme
    assert (
        f"release_draft_handoff_sha256: "
        f"`{artifact_bundle_summary['release_draft_handoff_sha256']}`"
    ) in readme
    assert f"release_draft_path: `{plan.release_draft_path}`" in readme
    assert (
        f"release_draft_path_sha256: "
        f"`{artifact_bundle_summary['release_draft_path_sha256']}`"
    ) in readme
    assert (
        f"release_draft_issues_sha256: "
        f"`{artifact_bundle_summary['release_draft_issues_sha256']}`"
    ) in readme
    assert "validation_command_count: `5`" in readme
    assert (
        "validation_commands_sha256: "
        f"`{artifact_bundle_summary['validation_commands_sha256']}`"
    ) in readme
    assert "review_checklist_count: `7`" in readme
    assert (
        "review_checklist_sha256: "
        f"`{artifact_bundle_summary['review_checklist_sha256']}`"
    ) in readme
    assert "create_issues_safety_contract_key_count: `5`" in readme
    assert (
        "create_issues_safety_contract_sha256: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_sha256']}`"
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
    assert "candidate_issue_gate_evidence_key_count: `10`" in readme
    assert (
        f"candidate_issue_gate_evidence_sha256: "
        f"`{artifact_bundle_summary['candidate_issue_gate_evidence_sha256']}`"
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
        "candidate_issue_gate_primary_required_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert "## Candidate Issue Gate Quick Summary" in readme
    assert readme.index("## Candidate Issue Gate Quick Summary") < readme.index("## Artifact Bundle Summary")
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
    assert "dry_run_supported: `true`" in readme
    assert "preflight_required: `true`" in readme
    assert "## Publication Handoff" in readme
    assert "publication_ok: `false`" in readme
    assert "candidate_issue_gate: `blocked_by_publication`" in readme
    assert "can_create_issues: `false`" in readme
    assert "gate_summary: Do not create candidate issues until the latest local release is publicly visible." in readme
    assert "gate_reason_code_count: `3`" in readme
    assert f"gate_reason_codes_sha256: `{_blocked_candidate_issue_gate()['reason_codes_sha256']}`" in readme
    assert "gate_required_action_count: `5`" in readme
    assert f"gate_required_actions_sha256: `{_blocked_candidate_issue_gate()['required_actions_sha256']}`" in readme
    assert "gate_reason_codes: `publication_not_published`, `dirty_worktree`, `release_draft_issues`" in readme
    assert "gate_reason_descriptions:" in readme
    assert "`publication_not_published`: The latest local release branch or tag is not visible upstream." in readme
    assert "`dirty_worktree`: The working tree has uncommitted changes that must be resolved first." in readme
    assert "`release_draft_issues`: The target release draft still has validation issues." in readme
    assert "gate_evidence_latest_tag: `v0.16.1`" in readme
    assert "gate_evidence_ahead_count: `2`" in readme
    assert "gate_evidence_worktree_clean: `false`" in readme
    assert "gate_evidence_release_draft_ok: `false`" in readme
    assert "gate_evidence_release_draft_issues: `2`" in readme
    assert "visibility: `dirty_worktree`" in readme
    assert (
        "visibility_summary: Worktree has uncommitted changes; "
        "resolve them before publishing release refs."
    ) in readme
    assert "latest_tag: `v0.16.1`" in readme
    assert "local_head: `abc123`" in readme
    assert "worktree_clean: `false`" in readme
    assert "publish_command_count: `1`" in readme
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
    assert "release_draft_ok: `false`" in readme
    assert "release_draft_path: `docs/releases/v0.16.2-draft.md`" in readme
    assert (
        f"release_draft_path_sha256: "
        f"`{_stable_json_sha256('docs/releases/v0.16.2-draft.md')}`"
    ) in readme
    assert "release_draft_issue_count: `2`" in readme
    assert "- release draft is missing" in readme
    assert "- release draft missing snippet: ## 发版前验证" in readme
    assert "Confirm release draft issues are resolved or intentionally deferred" in readme
    assert "Confirm Publication Next Actions are resolved or intentionally deferred" in readme
    assert "before running create-issues.sh" in readme
    assert "expected target URL, candidate commands" in readme
    assert "offline validation commands for each case" in readme
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
    assert "next_actions" in payload
