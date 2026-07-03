import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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

WEBSITE_DEPLOY_COMMAND = "cd site && vercel link --yes --project cliany.site && vercel --prod --yes"
WEBSITE_INSPECT_COMMAND = "cd site && vercel inspect www.cliany.site --wait --timeout 90s"
DISTRIBUTION_AUDIT_COMMAND = (
    "python scripts/check_release_publication.py --remote --distribution --json"
)
LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT = (
    "LLM live preflight is blocking candidate promotion. Paste the doctor JSON fields "
    "`summary.ready_for_explore`, `summary.llm_live_preflight`, "
    "`summary.capabilities.generate_adapters.ready`, `checks[llm_live].status`, "
    "`checks[llm_live].details.error_code`, `checks[llm_live].details.retryable`, "
    "`checks[llm_live].details.status_code`, `checks[llm_live].details.phase`, "
    "and `checks[llm_live].details.message`; keep `adapter_package` pending or blocked "
    "until `summary.llm_live_preflight.ready=true` and "
    "`summary.capabilities.generate_adapters.ready=true`."
)
DOCTOR_PREFLIGHT_BLOCKER_COMMENT = (
    "Doctor preflight is blocking candidate promotion. Paste the doctor JSON fields "
    "`summary.ready_for_explore`, `summary.capabilities.run_browser_workflows.ready`, "
    "`summary.capabilities.generate_adapters.ready`, `checks[cdp].status`, "
    "`checks[cdp].action`, `checks[llm_live].status`, "
    "`checks[llm_live].details.error_code`, `checks[llm_live].details.retryable`, "
    "`checks[llm_live].details.phase`, and `checks[llm_live].details.message`; "
    "keep `adapter_package` pending or blocked until "
    "`summary.ready_for_explore=true` and "
    "`summary.capabilities.generate_adapters.ready=true`."
)
DOCTOR_PREFLIGHT_EVIDENCE_FIELDS = [
    "summary.ready_for_explore",
    "summary.capabilities.run_browser_workflows.ready",
    "summary.capabilities.generate_adapters.ready",
    "checks[cdp].status",
    "checks[cdp].action",
    "checks[llm_live].status",
    "checks[llm_live].details.error_code",
    "checks[llm_live].details.retryable",
    "checks[llm_live].details.phase",
    "checks[llm_live].details.message",
]
DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE = {
    field: "<paste from doctor --llm-live --json>"
    for field in DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
}
DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS = {
    "summary.ready_for_explore": "data.summary.ready_for_explore",
    "summary.capabilities.run_browser_workflows.ready": (
        "data.summary.capabilities.run_browser_workflows.ready"
    ),
    "summary.capabilities.generate_adapters.ready": (
        "data.summary.capabilities.generate_adapters.ready"
    ),
    "checks[cdp].status": 'data.checks[name="cdp"].status',
    "checks[cdp].action": 'data.checks[name="cdp"].action',
    "checks[llm_live].status": 'data.checks[name="llm_live"].status',
    "checks[llm_live].details.error_code": (
        'data.checks[name="llm_live"].details.error_code'
    ),
    "checks[llm_live].details.retryable": (
        'data.checks[name="llm_live"].details.retryable'
    ),
    "checks[llm_live].details.phase": 'data.checks[name="llm_live"].details.phase',
    "checks[llm_live].details.message": (
        'data.checks[name="llm_live"].details.message'
    ),
}
DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT = len(
    DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE
)
DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256 = hashlib.sha256(
    json.dumps(
        DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()


def _stable_json_sha256(value: object) -> str:
    digest_source = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(digest_source).hexdigest()


def _command_sha256(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest() if command else ""


def _standard_release_flow_step_status_counts(
    steps: list[dict[str, object]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in steps:
        status = step.get("status")
        if status is None:
            continue
        status_key = str(status)
        counts[status_key] = counts.get(status_key, 0) + 1
    return counts


def _standard_release_flow_primary_step_name_with_status_prefix(
    steps: list[dict[str, object]],
    prefix: str,
) -> str | None:
    for step in steps:
        status = step.get("status")
        name = step.get("name")
        if status is not None and name is not None and str(status).startswith(prefix):
            return str(name)
    return None


def _target_tag_release_gate_fields(
    blockers: list[str] | None = None,
    *,
    target_tag: str = "v0.16.2",
) -> dict[str, object]:
    blocker_list = list(blockers or ["release draft validation failed"])
    return {
        "target_tag_release_gate_status": "blocked_by_readiness",
        "target_tag_release_gate_blocker_count": len(blocker_list),
        "target_tag_release_gate_blockers_sha256": _stable_json_sha256(blocker_list),
        "target_tag_release_gate_primary_blocker": blocker_list[0] if blocker_list else None,
        "target_tag_release_gate_required_action": (
            f"Clear release readiness blockers before creating target tag `{target_tag}`."
        ),
        "target_tag_release_gate_blockers": blocker_list,
    }


def _candidate_gate_target_tag_release_gate_fields(
    blockers: list[str] | None = None,
    *,
    target_tag: str = "v0.16.2",
) -> dict[str, object]:
    fields = _target_tag_release_gate_fields(blockers, target_tag=target_tag)
    return {
        f"publication_{key}": value
        for key, value in fields.items()
        if key != "target_tag_release_gate_blockers"
    }


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


def test_existing_case_promotion_summary_gets_doctor_preflight_fields() -> None:
    report = SimpleNamespace(
        promotion_evidence_summary={
            "primary_task": {
                "case_id": "pypi-project-search",
                "task": "adapter_package",
                "llm_live_preflight_required": True,
            },
            "pending_tasks": [
                {
                    "case_id": "pypi-project-search",
                    "task": "adapter_package",
                    "llm_live_preflight_required": True,
                }
            ],
        }
    )

    summary = plan_next_iteration._case_promotion_evidence_summary(report)

    assert summary["primary_task"]["doctor_preflight_evidence_fields"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
    )
    assert summary["primary_task"]["doctor_preflight_evidence_template"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE
    )
    assert summary["primary_task"]["doctor_preflight_evidence_selectors"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS
    )
    assert summary["primary_next_task"]["doctor_preflight_evidence_fields"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
    )
    assert summary["primary_next_task"]["doctor_preflight_evidence_template"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE
    )
    assert summary["primary_next_task"]["doctor_preflight_evidence_selectors"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS
    )
    assert summary["pending_tasks"][0]["doctor_preflight_evidence_fields"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
    )
    assert summary["pending_tasks"][0]["doctor_preflight_evidence_template"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE
    )
    assert summary["pending_tasks"][0]["doctor_preflight_evidence_selectors"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS
    )


def test_candidate_issue_script_uses_python3_default_with_override() -> None:
    script = "\n".join(
        plan_next_iteration._candidate_issue_script_lines(
            ["gh issue create --title 'Candidate'"],
            preflight_command="python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
        )
    )

    assert 'PYTHON_BIN="${PYTHON_BIN:-python3}"' in script
    assert (
        'if ! "$PYTHON_BIN" scripts/plan_next_iteration.py --target-version 0.16.2 --json >"$PREFLIGHT_JSON"; then'
    ) in script
    assert 'if ! "$PYTHON_BIN" - "$PREFLIGHT_JSON" <<\'PY\'' in script
    assert (
        'if ! python scripts/plan_next_iteration.py --target-version 0.16.2 --json >"$PREFLIGHT_JSON"; then'
    ) not in script
    assert 'if ! python - "$PREFLIGHT_JSON" <<\'PY\'' not in script


def test_candidate_issue_script_requires_review_ack_when_gate_needs_review() -> None:
    script = "\n".join(
        plan_next_iteration._candidate_issue_script_lines(
            ["gh issue create --title 'Candidate'"],
            preflight_command="python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
        )
    )

    assert "CLIANY_CREATE_ISSUES_ACK_REVIEW" in script
    assert 'os.environ.get("CLIANY_CREATE_ISSUES_ACK_REVIEW") != "1"' in script
    assert '"Set CLIANY_CREATE_ISSUES_ACK_REVIEW=1 after maintainer review to continue."' in script
    assert "file=sys.stderr" in script
    assert "sys.exit(1)" in script


def _pypi_promotion_command_plan(*, explore_query: str = "search Python packages") -> list[dict[str, object]]:
    explore_command = f'cliany-site explore "https://pypi.org" "{explore_query}" --json'
    metadata_command = (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
    )
    smoke_command = "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json"
    return [
        {
            "task": "llm_live_preflight",
            "command": "cliany-site doctor --llm-live --json",
            "command_sha256": hashlib.sha256(
                b"cliany-site doctor --llm-live --json"
            ).hexdigest(),
            "source": "doctor.llm_live",
            "missing": False,
        },
        {
            "task": "adapter_package",
            "command": explore_command,
            "command_sha256": hashlib.sha256(explore_command.encode("utf-8")).hexdigest(),
            "source": "commands.explore",
            "missing": False,
        },
        {
            "task": "metadata_validation",
            "command": metadata_command,
            "command_sha256": hashlib.sha256(metadata_command.encode("utf-8")).hexdigest(),
            "source": "candidate_package_validation_command",
            "missing": False,
        },
        {
            "task": "online_smoke",
            "command": smoke_command,
            "command_sha256": hashlib.sha256(smoke_command.encode("utf-8")).hexdigest(),
            "source": "commands.adapter",
            "missing": False,
        },
    ]


def _pypi_promotion_command_plan_summary() -> dict[str, object]:
    plan = _pypi_promotion_command_plan()
    missing_command_count = sum(1 for item in plan if item["missing"])
    return {
        "command_count": len(plan),
        "missing_command_count": missing_command_count,
        "all_declared": bool(plan) and missing_command_count == 0,
    }


def _pypi_primary_runbook(*, explore_query: str = "search Python packages") -> list[dict[str, object]]:
    return [
        {
            "step": "llm_live_preflight",
            "command": "cliany-site doctor --llm-live --json",
            "required": True,
            "handoff": plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE,
        },
        {
            "step": "adapter_package",
            "command": f'cliany-site explore "https://pypi.org" "{explore_query}" --json',
            "required": True,
            "handoff": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        },
        {
            "step": "acceptance",
            "command": "",
            "required": True,
            "handoff": (
                "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
                "package path or GitHub Release asset name."
            ),
        },
    ]


def test_candidate_issue_body_checks_complete_tasks():
    issue_body = plan_next_iteration._candidate_issue_body(
        case_id="mixed-candidate",
        target_url="https://example.test/search",
        commands=["cliany-site example.test search --json"],
        offline_commands=["python scripts/validate_cases.py --strict"],
        expected_adapter_package="example.test-<version>.cliany-adapter.tar.gz",
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
    assert "- Expected adapter package: `example.test-<version>.cliany-adapter.tar.gz`" in issue_body
    assert "- Next action: Run read-only smoke." in issue_body
    assert "- Acceptance criteria: Paste the read-only adapter command JSON envelope summary" in issue_body
    assert "## Promotion Command Plan" in issue_body
    assert "- `online_smoke`: `cliany-site example.test search --json`" in issue_body
    assert "## LLM Preflight Gate" in issue_body
    assert "- Command: `cliany-site doctor --llm-live --json`" in issue_body
    assert (
        "- Command SHA-256: `"
        f"{hashlib.sha256(b'cliany-site doctor --llm-live --json').hexdigest()}`"
        in issue_body
    )
    assert "generate_adapters.ready=false" in issue_body
    assert "E_LLM_UNAVAILABLE" in issue_body
    assert "## LLM Preflight Blocker Comment" in issue_body
    assert LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT in issue_body
    assert "## Doctor Preflight Blocker Comment" in issue_body
    assert DOCTOR_PREFLIGHT_BLOCKER_COMMENT in issue_body
    assert "## Doctor Preflight Evidence Fields" in issue_body
    assert "- `summary.capabilities.run_browser_workflows.ready`" in issue_body
    assert "- `checks[cdp].action`" in issue_body
    assert "## Doctor Preflight Evidence Template" in issue_body
    assert "- `summary.ready_for_explore`: `<paste from doctor --llm-live --json>`" in issue_body
    assert (
        "- `checks[llm_live].details.error_code`: "
        "`<paste from doctor --llm-live --json>`"
        in issue_body
    )
    assert "## Acceptance Criteria" in issue_body
    assert "`adapter_package`: Attach the generated <domain>-<version>.cliany-adapter.tar.gz" in issue_body
    assert "`metadata_validation`: Paste `python scripts/validate_cases.py" in issue_body
    assert "- [x] `adapter_package`: Build adapter package." in issue_body
    assert "  - Acceptance criteria: Attach the generated <domain>-<version>.cliany-adapter.tar.gz" in issue_body
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
                    adapter_domain="pypi.org",
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
                    adapter_domain="www.npmjs.com",
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


def _published_release_with_unreleased_head_report() -> SimpleNamespace:
    return SimpleNamespace(
        ok=False,
        repo_root="/repo/cliany.site",
        branch="master",
        upstream="origin/master",
        remote="origin",
        local_head="new123",
        upstream_head="new123",
        ahead_count=0,
        behind_count=0,
        latest_tag="v0.16.1",
        tag_commit="old123",
        tag_points_at_head=False,
        tag_commit_in_upstream=True,
        branch_published=True,
        tag_published=True,
        remote_branch_head="new123",
        remote_tag_commit="old123",
        remote_checked=True,
        worktree_clean=True,
        worktree_status=[],
        next_actions=[
            "Move to the `v0.16.1` commit or create a new release tag at HEAD before publishing.",
        ],
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
            "publication_target_tag": "v0.16.2",
            "publication_target_tag_status": "blocked_by_worktree",
            "publication_target_tag_primary_command": "git tag v0.16.2",
            "publication_target_tag_commands_sha256": _stable_json_sha256(
                ["git tag v0.16.2", "git push origin v0.16.2"]
            ),
            "publication_target_tag_required_action": (
                "Commit, stash, or discard local worktree changes before creating target tag "
                "`v0.16.2`."
            ),
            **_candidate_gate_target_tag_release_gate_fields(),
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
    assert plan.case_promotion_evidence_summary["primary_next_task"]["priority_rank"] == 1
    assert plan.case_promotion_evidence_summary["primary_next_task"]["priority_reason"] == (
        "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0"
    )
    assert (
        plan.case_promotion_evidence_summary["primary_next_task"]["expected_adapter_package"]
        == "pypi.org-<version>.cliany-adapter.tar.gz"
    )
    assert plan.candidate_promotions[0].case_id == "pypi-project-search"
    assert plan.candidate_promotions[0].issue_template_command == (
        "cliany-site cases --case-id pypi-project-search --issue-template"
    )
    assert plan.candidate_promotions[0].issue_template_json_command == (
        "cliany-site cases --case-id pypi-project-search --issue-template --json"
    )
    assert (
        plan.candidate_promotions[0].expected_adapter_package
        == "pypi.org-<version>.cliany-adapter.tar.gz"
    )
    assert plan.candidate_promotions[0].priority_rank == 1
    assert plan.candidate_promotions[0].priority_reason == (
        "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0"
    )


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
    assert plan.publication_tag_publish_decision["target_tag"] == "v0.16.2"
    assert (
        plan.publication_tag_publish_decision["target_tag_status"]
        == "create_target_tag_at_head"
    )
    assert plan.publication_tag_publish_decision["target_tag_commands"] == [
        "git tag v0.16.2",
        "git push origin v0.16.2",
    ]
    assert plan.publication_tag_publish_decision["target_tag_commands_sha256"] == (
        _stable_json_sha256(plan.publication_tag_publish_decision["target_tag_commands"])
    )
    assert (
        plan.publication_tag_publish_decision["target_tag_release_gate_status"]
        == "blocked_by_readiness"
    )
    assert (
        plan.publication_tag_publish_decision["target_tag_release_gate_primary_blocker"]
        == "release draft validation failed"
    )
    assert plan.next_actions[:3] == [
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
        (
            "After final release readiness is clean, create target tag `v0.16.2` at HEAD and push it "
            "after the branch is published. Commands: `git tag v0.16.2` then "
            "`git push origin v0.16.2`."
        ),
        "Rerun with `--remote` when network access is available to verify live remote refs.",
    ]
    assert not any("push `master` and tag `v0.16.1`" in action for action in plan.next_actions)
    assert not any("Push tag `v0.16.1`" in action for action in plan.next_actions)


def test_plan_prefers_standard_release_flow_primary_action(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    standard_primary_action = (
        "Move to the `v0.16.1` commit or create a new release tag at HEAD before publishing."
    )
    readiness.standard_release_flow = {
        "status": "blocked",
        "target_version": "0.16.2",
        "target_tag": "v0.16.2",
        "blocker_count": 2,
        "blockers_sha256": _stable_json_sha256(
            ["commit days 2/3", "latest release tag does not point at HEAD"]
        ),
        "blockers": ["commit days 2/3", "latest release tag does not point at HEAD"],
        "primary_next_action": standard_primary_action,
        "command_count": 3,
        "commands_sha256": _stable_json_sha256(
            [
                "python scripts/release_readiness.py --strict --target-version 0.16.2",
                "git tag v0.16.2",
                "git push origin v0.16.2",
            ]
        ),
        "commands": [
            "python scripts/release_readiness.py --strict --target-version 0.16.2",
            "git tag v0.16.2",
            "git push origin v0.16.2",
        ],
    }

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_tag_mismatch_publication_report(),
    )
    data = plan.to_dict()

    assert plan.next_actions[0] == standard_primary_action
    assert plan.next_actions[1] == (
        "After final release readiness is clean, create target tag `v0.16.2` at HEAD and push it "
        "after the branch is published. Commands: `git tag v0.16.2` then "
        "`git push origin v0.16.2`."
    )
    assert data["primary_next_action"] == standard_primary_action
    assert data["standard_release_flow"] == readiness.standard_release_flow
    assert data["standard_release_flow_status"] == "blocked"
    assert data["standard_release_flow_primary_next_action"] == standard_primary_action
    assert data["standard_release_flow_command_count"] == 3
    assert data["standard_release_flow_commands_sha256"] == (
        readiness.standard_release_flow["commands_sha256"]
    )
    assert data["standard_release_flow_step_count"] == 0
    assert data["standard_release_flow_step_names"] == []
    assert data["standard_release_flow_step_names_sha256"] == _stable_json_sha256([])
    assert data["standard_release_flow_steps_sha256"] == _stable_json_sha256([])
    assert data["standard_release_flow_first_step_name"] is None
    assert data["standard_release_flow_last_step_name"] is None
    assert data["standard_release_flow_step_boundary_sha256"] == _stable_json_sha256(
        {"first_step_name": None, "last_step_name": None}
    )
    assert data["standard_release_flow_step_status_counts"] == {}
    assert data["standard_release_flow_step_status_counts_sha256"] == _stable_json_sha256(
        {}
    )
    assert data["standard_release_flow_primary_blocked_step_name"] is None
    assert data["standard_release_flow_primary_blocked_step_status"] is None
    assert data["standard_release_flow_primary_blocked_step_status_sha256"] is None
    assert data["standard_release_flow_primary_blocked_step_command"] is None
    assert data["standard_release_flow_primary_blocked_step_command_sha256"] is None
    assert data["standard_release_flow_primary_blocked_step_action"] is None
    assert data["standard_release_flow_primary_blocked_step_action_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_name"] is None
    assert data["standard_release_flow_primary_pending_step_status"] is None
    assert data["standard_release_flow_primary_pending_step_status_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_command"] is None
    assert data["standard_release_flow_primary_pending_step_command_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_action"] is None
    assert data["standard_release_flow_primary_pending_step_action_sha256"] is None


def test_plan_carries_readiness_pause_action_for_daily_release_cap(tmp_path, capsys):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    pause_action = (
        "Pause release tagging until the next day; creating `v0.16.2` today would make "
        "release tags `4/3`."
    )
    cadence_action = (
        "Ship verified slices on `1` more unique commit days this week; current commit days "
        "are `2/3`. Use `docs/weekly-maintainer-loop.md` to pick the next slice."
    )
    strict_command = "python scripts/release_readiness.py --strict --target-version 0.16.2"
    release_notes_action = "Move CHANGELOG.md Unreleased entries into `## [0.16.2] - <date>`."
    readiness.blockers = [
        "creating target tag v0.16.2 today would exceed the daily release cap 4/3"
    ]
    readiness.next_actions = [cadence_action, pause_action]
    readiness.daily_release_cap_blocked = True
    readiness.daily_release_resume_date = "2026-06-11"
    readiness.standard_release_flow = {
        "status": "blocked",
        "target_version": "0.16.2",
        "target_tag": "v0.16.2",
        "primary_next_action": (
            "Move to the `v0.16.1` commit or create a new release tag at HEAD before publishing."
        ),
        "steps": [
            {
                "name": "strict_release_readiness",
                "status": "blocked",
                "command": strict_command,
            },
            {
                "name": "release_notes",
                "status": "pending",
                "action": release_notes_action,
            },
        ],
    }

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_tag_mismatch_publication_report(),
    )
    data = plan.to_dict()

    assert plan.next_actions[0] == pause_action
    assert plan.daily_release_cap_blocked is True
    assert plan.daily_release_resume_date == "2026-06-11"
    assert pause_action in plan.next_actions
    assert pause_action in data["next_actions"]
    assert data["daily_release_cap_blocked"] is True
    assert data["daily_release_resume_date"] == "2026-06-11"
    assert data["daily_release_resume_date_sha256"] == _stable_json_sha256("2026-06-11")
    assert data["standard_release_flow_primary_blocked_step_name"] == (
        "strict_release_readiness"
    )
    assert data["standard_release_flow_primary_blocked_step_status"] == "blocked"
    assert data["standard_release_flow_primary_blocked_step_status_sha256"] == (
        _stable_json_sha256("blocked")
    )
    assert data["standard_release_flow_primary_blocked_step_command"] == strict_command
    assert data["standard_release_flow_primary_blocked_step_command_sha256"] == (
        _stable_json_sha256(strict_command)
    )
    assert data["standard_release_flow_primary_blocked_step_action"] is None
    assert data["standard_release_flow_primary_blocked_step_action_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_name"] == "release_notes"
    assert data["standard_release_flow_primary_pending_step_status"] == "pending"
    assert data["standard_release_flow_primary_pending_step_status_sha256"] == (
        _stable_json_sha256("pending")
    )
    assert data["standard_release_flow_primary_pending_step_command"] is None
    assert data["standard_release_flow_primary_pending_step_command_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_action"] == release_notes_action
    assert data["standard_release_flow_primary_pending_step_action_sha256"] == (
        _stable_json_sha256(release_notes_action)
    )
    assert cadence_action in plan.next_actions
    assert "Ship verified slices on `1` more unique commit days this week." not in plan.next_actions
    assert not any(
        "create a new release tag at HEAD" in action
        for action in plan.publication_next_actions
    )
    assert not any(
        "create a new release tag at HEAD" in action
        for action in data["publication_next_actions"]
    )
    assert plan.publication_tag_publish_decision["status"] == "blocked_by_daily_release_cap"
    assert (
        plan.publication_tag_publish_decision["required_action"]
        == plan.publication_tag_publish_decision["target_tag_required_action"]
    )
    assert (
        plan.publication_tag_publish_decision["target_tag_release_gate_required_action"]
        == plan.publication_tag_publish_decision["target_tag_required_action"]
    )
    assert "create a new release tag at HEAD" not in (
        plan.publication_tag_publish_decision["required_action"] or ""
    )
    assert plan.publication_tag_publish_decision["target_tag_commands"] == []
    assert plan.publication_tag_publish_decision["target_tag_command_count"] == 0
    assert not any("create a new release tag at HEAD" in action for action in plan.next_actions)
    assert not any("git tag v0.16.2" in action for action in plan.next_actions)

    plan_next_iteration._print_text(plan)
    output = capsys.readouterr().out
    assert "daily_release_cap_blocked: true" in output
    assert "daily_release_resume_date: 2026-06-11" in output
    assert (
        "daily_release_resume_date_sha256: "
        f"{_stable_json_sha256('2026-06-11')}"
    ) in output

    report_path = tmp_path / "reports" / "daily-cap-plan.md"
    plan_next_iteration._write_markdown_report(plan, report_path)
    text = report_path.read_text(encoding="utf-8")
    assert "| daily_release_cap_blocked | `true` |" in text
    assert "| daily_release_resume_date | `2026-06-11` |" in text
    assert (
        "| daily_release_resume_date_sha256 | "
        f"`{_stable_json_sha256('2026-06-11')}` |"
    ) in text


def test_handoff_payload_projects_primary_release_and_candidate_actions(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    readiness.blockers = [
        "creating target tag v0.16.2 today would exceed the daily release cap 4/3"
    ]
    readiness.daily_release_cap_blocked = True
    readiness.daily_release_resume_date = "2026-06-11"
    readiness.standard_release_flow = {
        "status": "blocked",
        "target_version": "0.16.2",
        "target_tag": "v0.16.2",
        "primary_next_action": "Pause release tagging until tomorrow.",
        "steps": [
            {
                "name": "strict_release_readiness",
                "status": "blocked",
                "command": "python scripts/release_readiness.py --strict --target-version 0.16.2",
            },
            {
                "name": "release_notes",
                "status": "pending",
                "action": "Move CHANGELOG.md Unreleased entries into the target release.",
            },
        ],
    }

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_published_release_with_unreleased_head_report(),
    )

    payload = plan_next_iteration._handoff_payload(plan)

    assert payload["schema_version"] == 1
    assert payload["current_version"] == "0.16.1"
    assert payload["target_version"] == "0.16.2"
    assert payload["daily_release_cap_blocked"] is True
    assert payload["daily_release_resume_date"] == "2026-06-11"
    assert payload["primary_next_action"] == plan.next_actions[0]
    assert payload["next_action_count"] == len(plan.next_actions)
    assert payload["blocker_count"] == len(plan.blockers)
    assert payload["standard_release_flow_status"] == "blocked"
    assert payload["standard_release_flow_primary_blocked_step_name"] == (
        "strict_release_readiness"
    )
    assert payload["standard_release_flow_primary_pending_step_name"] == "release_notes"
    assert payload["publication_summary"]["status"] == "published_with_unreleased_head"
    assert payload["publication_summary"]["latest_tag"] == "v0.16.1"
    assert payload["publication_summary"]["target_tag"] == "v0.16.2"
    assert payload["publication_summary"]["tag_decision_status"] == (
        "blocked_by_daily_release_cap"
    )
    assert payload["primary_candidate"]["case_id"] == "pypi-project-search"
    assert payload["primary_candidate"]["task"] == "adapter_package"
    assert payload["primary_candidate"]["expected_adapter_package"] == (
        "pypi.org-<version>.cliany-adapter.tar.gz"
    )
    assert payload["primary_candidate"]["llm_live_preflight_command"] == (
        "cliany-site doctor --llm-live --json"
    )
    assert payload["primary_candidate"]["issue_template_command"] == (
        "cliany-site cases --case-id pypi-project-search --issue-template"
    )
    assert payload["primary_candidate"]["evidence_bundle_json_command"] == (
        "cliany-site cases --case-id pypi-project-search --evidence-bundle --json"
    )
    assert payload["validation_commands"] == plan.validation_commands
    assert payload["handoff_sha256"] == _stable_json_sha256(
        {key: value for key, value in payload.items() if key != "handoff_sha256"}
    )


def test_main_handoff_json_outputs_compact_payload(monkeypatch, tmp_path, capsys):
    _write_pyproject(tmp_path, version="0.16.256")
    real_build_plan = plan_next_iteration.build_plan

    def fake_build_plan(root, **kwargs):
        readiness = _readiness_report()
        target_version = kwargs.get("target_version")
        if target_version:
            readiness.target_version = target_version
            readiness.draft.target_version = target_version
        return real_build_plan(
            tmp_path,
            readiness_report=readiness,
            publication_report=_published_release_with_unreleased_head_report(),
            **kwargs,
        )

    monkeypatch.setattr(plan_next_iteration, "build_plan", fake_build_plan)

    exit_code = plan_next_iteration.main(["--target-version", "0.16.257", "--handoff-json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["target_version"] == "0.16.257"
    assert payload["primary_candidate"]["case_id"] == "pypi-project-search"
    assert payload["primary_candidate"]["task"] == "adapter_package"
    assert "candidate_promotions" not in payload
    assert "case_promotion_evidence_summary" not in payload
    assert payload["handoff_sha256"] == _stable_json_sha256(
        {key: value for key, value in payload.items() if key != "handoff_sha256"}
    )


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
            "publication_target_tag": "v0.16.2",
            "publication_target_tag_status": "create_target_tag_at_head",
            "publication_target_tag_primary_command": "git tag v0.16.2",
            "publication_target_tag_commands_sha256": _stable_json_sha256(
                ["git tag v0.16.2", "git push origin v0.16.2"]
            ),
            "publication_target_tag_required_action": (
                "After final release readiness is clean, create target tag `v0.16.2` "
                "at HEAD and push it after the branch is published."
            ),
            **_candidate_gate_target_tag_release_gate_fields(),
            "release_draft_ok": False,
            "release_draft_path": "docs/releases/v0.16.2-draft.md",
            "release_draft_issue_count": 2,
        },
    }


def test_plan_treats_published_release_with_unreleased_head_as_visible(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=_published_release_with_unreleased_head_report(),
    )

    assert plan.publication_visibility == {
        "status": "published_with_unreleased_head",
        "summary": (
            "Latest release `v0.16.1` is visible on `origin`; HEAD contains unreleased "
            "changes that need a new target tag before the next release."
        ),
    }
    assert "latest local release is not published" not in plan.blockers
    assert plan.recommended_theme == "真实案例库"
    assert plan.candidate_issue_gate["status"] == "review_required"
    assert plan.candidate_issue_gate["reason_codes"] == ["release_draft_issues"]
    assert plan.candidate_issue_gate["evidence"]["publication_visibility_status"] == (
        "published_with_unreleased_head"
    )


def test_candidate_issue_gate_surfaces_release_readiness_blocker_after_publication(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    pause_action = (
        "Pause release tagging until the next day; creating `v0.16.2` today would make "
        "release tags `4/3`."
    )
    readiness.blockers = [
        "creating target tag v0.16.2 today would exceed the daily release cap 4/3"
    ]
    readiness.next_actions = [pause_action]
    readiness.daily_release_cap_blocked = True
    readiness.daily_release_resume_date = "2026-06-11"
    readiness.draft = SimpleNamespace(
        ok=True,
        path="/tmp/project/docs/releases/v0.16.2-draft.md",
        target_version="0.16.2",
        issues=[],
    )

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_published_release_with_unreleased_head_report(),
    )

    assert plan.candidate_issue_gate["status"] == "review_required"
    assert plan.candidate_issue_gate["can_create_issues"] is True
    assert plan.candidate_issue_gate["requires_maintainer_review"] is True
    assert plan.candidate_issue_gate["reason_codes"] == ["release_readiness_blockers"]
    assert (
        plan.candidate_issue_gate["reason_descriptions"]["release_readiness_blockers"]
        == "The target release is still blocked by release readiness."
    )
    assert plan.candidate_issue_gate["required_actions"] == [pause_action]
    assert plan.candidate_issue_gate["primary_required_action"] == pause_action
    assert (
        plan.candidate_issue_gate["evidence"]["release_readiness_primary_blocker"]
        == "creating target tag v0.16.2 today would exceed the daily release cap 4/3"
    )
    assert plan.candidate_issue_gate["evidence"]["release_readiness_blocker_count"] == 1


def test_candidate_issue_gate_deduplicates_required_actions(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    duplicate_action = (
        "Commit, stash, or discard local worktree changes before publishing release refs."
    )
    daily_cap_action = (
        "Pause release tagging until the next day; creating `v0.16.2` today would make "
        "release tags `4/3`."
    )
    readiness.blockers = [
        "working tree is dirty",
        "creating target tag v0.16.2 today would exceed the daily release cap 4/3",
    ]
    readiness.next_actions = [duplicate_action, daily_cap_action]
    readiness.draft = SimpleNamespace(
        ok=True,
        path="/tmp/project/docs/releases/v0.16.2-draft.md",
        target_version="0.16.2",
        issues=[],
    )
    expected_actions = [
        duplicate_action,
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
        "Push tag `v0.16.1` after the branch is published.",
        daily_cap_action,
    ]

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_publication_report(),
    )

    assert plan.candidate_issue_gate["required_actions"] == expected_actions
    assert plan.candidate_issue_gate["required_action_count"] == len(expected_actions)
    assert plan.candidate_issue_gate["required_actions_sha256"] == _stable_json_sha256(
        expected_actions
    )
    assert plan.candidate_issue_gate["primary_required_action"] == duplicate_action


def test_plan_deduplicates_publication_next_actions(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    publication = _publication_report()
    duplicate_action = (
        "- Commit, stash, or discard local worktree changes before publishing release refs."
    )
    publication.next_actions = [
        duplicate_action,
        duplicate_action,
        "- Push `master` to `origin`; local branch is ahead by `2` commits.",
    ]
    expected_actions = [
        "Commit, stash, or discard local worktree changes before publishing release refs.",
        "Push `master` to `origin`; local branch is ahead by `2` commits.",
    ]

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=publication,
    )
    data = plan.to_dict()

    assert plan.publication_next_actions == expected_actions
    assert data["publication_next_actions"] == expected_actions
    assert data["publication_next_action_count"] == len(expected_actions)
    assert data["publication_next_actions_sha256"] == _stable_json_sha256(expected_actions)
    assert data["publication_primary_next_action"] == expected_actions[0]


def test_plan_deduplicates_publication_publish_commands(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    publication = _tag_mismatch_publication_report()
    publication.publish_commands = [
        "git push origin master",
        "git push origin master",
        "python scripts/check_release_publication.py --remote --json",
    ]
    expected_commands = [
        "git push origin master",
        "python scripts/check_release_publication.py --remote --json",
    ]

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=_readiness_report(),
        publication_report=publication,
    )
    data = plan.to_dict()

    assert plan.publication_publish_commands == expected_commands
    assert data["publication_publish_commands"] == expected_commands
    assert data["publication_publish_command_count"] == len(expected_commands)
    assert data["publication_publish_commands_sha256"] == _stable_json_sha256(
        expected_commands
    )
    assert data["publication_primary_publish_command"] == expected_commands[0]


def test_release_draft_handoff_deduplicates_required_actions(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    readiness.draft.issues = [
        "release draft is missing",
        "release draft is missing",
        "release draft missing snippet: ## 发版前验证",
    ]
    expected_actions = [
        "Resolve release draft issue: release draft is missing",
        "Resolve release draft issue: release draft missing snippet: ## 发版前验证",
    ]

    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_publication_report(),
    )
    handoff = plan_next_iteration._release_draft_handoff(plan)

    assert handoff["release_draft_issue_count"] == 3
    assert handoff["release_draft_issues"] == readiness.draft.issues
    assert handoff["release_draft_required_actions"] == expected_actions
    assert handoff["release_draft_required_action_count"] == len(expected_actions)
    assert handoff["release_draft_required_actions_sha256"] == _stable_json_sha256(
        expected_actions
    )
    assert handoff["primary_required_action"] == expected_actions[0]


def test_issue_artifacts_surface_release_readiness_blocker_aliases(tmp_path):
    _write_pyproject(tmp_path, version="0.16.1")
    readiness = _readiness_report()
    readiness_blocker = (
        "creating target tag v0.16.2 today would exceed the daily release cap 4/3"
    )
    pause_action = (
        "Pause release tagging until the next day; creating `v0.16.2` today would make "
        "release tags `4/3`."
    )
    readiness.blockers = [readiness_blocker]
    readiness.next_actions = [pause_action]
    readiness.daily_release_cap_blocked = True
    readiness.daily_release_resume_date = "2026-06-11"
    readiness.draft = SimpleNamespace(
        ok=True,
        path="/tmp/project/docs/releases/v0.16.2-draft.md",
        target_version="0.16.2",
        issues=[],
    )
    plan = plan_next_iteration.build_plan(
        tmp_path,
        readiness_report=readiness,
        publication_report=_published_release_with_unreleased_head_report(),
    )
    issues_dir = tmp_path / "issue-artifacts"

    plan_next_iteration._write_candidate_issue_files(plan, issues_dir)

    artifact_manifest = json.loads(
        (issues_dir / "artifact-manifest.json").read_text(encoding="utf-8")
    )
    publication_handoff = json.loads(
        (issues_dir / "publication-handoff.json").read_text(encoding="utf-8")
    )
    readme = (issues_dir / "README.md").read_text(encoding="utf-8")
    quick_summary = readme[
        readme.index("## Candidate Issue Gate Quick Summary") : readme.index(
            "## Commit Cadence"
        )
    ]

    assert publication_handoff["release_readiness_blocker_count"] == 1
    assert publication_handoff["release_readiness_primary_blocker"] == readiness_blocker
    assert publication_handoff["release_readiness_blockers_sha256"] == _stable_json_sha256(
        [readiness_blocker]
    )
    assert publication_handoff["daily_release_cap_blocked"] is True
    assert publication_handoff["daily_release_resume_date"] == "2026-06-11"
    assert publication_handoff["daily_release_resume_date_sha256"] == _stable_json_sha256(
        "2026-06-11"
    )
    assert artifact_manifest["daily_release_cap_blocked"] is True
    assert artifact_manifest["daily_release_resume_date"] == "2026-06-11"
    assert artifact_manifest["artifact_bundle_summary"]["daily_release_cap_blocked"] is True
    assert (
        artifact_manifest["artifact_bundle_summary"]["daily_release_resume_date"]
        == "2026-06-11"
    )
    assert "- release_readiness_blocker_count: `1`" in quick_summary
    assert f"- release_readiness_primary_blocker: `{readiness_blocker}`" in quick_summary
    assert (
        f"- release_readiness_blockers_sha256: "
        f"`{_stable_json_sha256([readiness_blocker])}`"
    ) in quick_summary
    assert "- daily_release_cap_blocked: `true`" in quick_summary
    assert "- daily_release_resume_date: `2026-06-11`" in quick_summary
    assert (
        f"- daily_release_resume_date_sha256: "
        f"`{_stable_json_sha256('2026-06-11')}`"
    ) in quick_summary


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
    preflight_command = "cliany-site doctor --llm-live --json"
    explore_command = 'cliany-site explore "https://pypi.org" "search Python packages" --json'
    metadata_command = (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
    )
    smoke_command = "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json"

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
        "release_tags_today": [],
        "release_count_today": 0,
        "max_daily_releases": 3,
        "daily_release_limit_ok": True,
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
    assert data["publication_blockers"] == [
        "publication worktree is dirty",
        "latest local release is not published",
        "latest local release tag is not published",
    ]
    assert data["publication_blocker_count"] == len(data["publication_blockers"])
    assert data["publication_blockers_sha256"] == _stable_json_sha256(
        data["publication_blockers"]
    )
    assert data["publication_primary_blocker"] == data["publication_blockers"][0]
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
    assert data["case_promotion_evidence_summary_sha256"] == _stable_json_sha256(
        data["case_promotion_evidence_summary"]
    )
    assert data["case_promotion_command_plan_summary_sha256"] == _stable_json_sha256(
        data["case_promotion_command_plan_summary"]
    )
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
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "llm_live_preflight_required": True,
        "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
        "llm_live_preflight_command_sha256": _command_sha256(
            "cliany-site doctor --llm-live --json"
        ),
        "llm_live_preflight_blocker_note": (
            plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
        ),
        "llm_live_preflight_evidence_fields": list(
            plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS
        ),
        "doctor_preflight_evidence_fields": list(
            plan_next_iteration.DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
        ),
        "doctor_preflight_evidence_template": DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
        "doctor_preflight_evidence_selectors": DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS,
        "doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
        ),
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
    primary_task = data["case_promotion_evidence_summary"]["primary_next_task"]
    assert (
        data["case_promotion_evidence_primary_expected_adapter_package"]
        == primary_task["expected_adapter_package"]
    )
    assert (
        data["case_promotion_evidence_primary_acceptance_criteria"]
        == plan_next_iteration.CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA["adapter_package"]
    )
    assert (
        data["case_promotion_evidence_primary_acceptance_criteria_sha256"]
        == _stable_json_sha256(
            plan_next_iteration.CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA["adapter_package"]
        )
    )
    assert data["case_promotion_evidence_primary_priority_rank"] == primary_task["priority_rank"]
    assert (
        data["case_promotion_evidence_primary_priority_reason"]
        == primary_task["priority_reason"]
    )
    primary_promotion = data["candidate_promotions"][0]
    assert (
        data["case_promotion_evidence_primary_issue_template_command"]
        == primary_promotion["issue_template_command"]
    )
    assert (
        data["case_promotion_evidence_primary_issue_template_json_command"]
        == primary_promotion["issue_template_json_command"]
    )
    assert (
        data["case_promotion_evidence_primary_evidence_bundle_command"]
        == primary_promotion["evidence_bundle_command"]
    )
    assert (
        data["case_promotion_evidence_primary_evidence_bundle_json_command"]
        == primary_promotion["evidence_bundle_json_command"]
    )
    primary_runbook = data["case_promotion_evidence_summary"]["primary_next_task_runbook"]
    primary_runbook_steps = [step["step"] for step in primary_runbook]
    assert data["case_promotion_evidence_primary_runbook"] == primary_runbook
    assert data["case_promotion_evidence_primary_runbook_step_count"] == 3
    assert data["case_promotion_evidence_primary_runbook_steps"] == [
        "llm_live_preflight",
        "adapter_package",
        "acceptance",
    ]
    assert data["case_promotion_evidence_primary_runbook_steps_sha256"] == _stable_json_sha256(
        primary_runbook_steps
    )
    assert data["case_promotion_evidence_primary_runbook_first_step"] == "llm_live_preflight"
    assert (
        data["case_promotion_evidence_primary_runbook_first_command"]
        == "cliany-site doctor --llm-live --json"
    )
    assert data["case_promotion_evidence_primary_runbook_first_command_sha256"] == (
        _command_sha256("cliany-site doctor --llm-live --json")
    )
    assert data["case_promotion_evidence_primary_llm_live_preflight_required"] is True
    assert (
        data["case_promotion_evidence_primary_llm_live_preflight_command"]
        == "cliany-site doctor --llm-live --json"
    )
    assert data[
        "case_promotion_evidence_primary_llm_live_preflight_command_sha256"
    ] == _command_sha256("cliany-site doctor --llm-live --json")
    assert (
        data["case_promotion_evidence_primary_llm_live_preflight_blocker_note"]
        == plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
    )
    assert (
        data["case_promotion_evidence_primary_llm_live_preflight_blocker_comment"]
        == LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT
    )
    assert (
        data["case_promotion_evidence_primary_doctor_preflight_blocker_comment"]
        == DOCTOR_PREFLIGHT_BLOCKER_COMMENT
    )
    assert (
        data[
            "case_promotion_evidence_primary_doctor_preflight_evidence_template_field_count"
        ]
        == DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
    )
    assert (
        data["case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256"]
        == DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
    )
    markdown = plan_next_iteration._render_markdown(plan)
    assert (
        "| case_promotion_evidence_primary_llm_live_preflight_blocker_comment | "
        f"{plan_next_iteration._summary_inline_code(LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT)} |"
    ) in markdown
    assert (
        "| case_promotion_evidence_primary_doctor_preflight_blocker_comment | "
        f"{plan_next_iteration._summary_inline_code(DOCTOR_PREFLIGHT_BLOCKER_COMMENT)} |"
    ) in markdown
    assert (
        "| case_promotion_evidence_primary_doctor_preflight_evidence_template_field_count | "
        f"`{DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT}` |"
    ) in markdown
    assert (
        "| case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256 | "
        f"`{DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256}` |"
    ) in markdown
    assert (
        "| case_promotion_evidence_primary_llm_live_preflight_command_sha256 | "
        f"`{_command_sha256('cliany-site doctor --llm-live --json')}` |"
    ) in markdown
    llm_preflight_fields = data["case_promotion_evidence_summary"][
        "llm_live_preflight_evidence_fields"
    ]
    assert llm_preflight_fields == list(plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS)
    assert data["case_promotion_llm_live_preflight_evidence_fields"] == llm_preflight_fields
    assert data["case_promotion_llm_live_preflight_evidence_field_count"] == len(
        llm_preflight_fields
    )
    assert data["case_promotion_llm_live_preflight_evidence_fields_sha256"] == (
        _stable_json_sha256(llm_preflight_fields)
    )
    assert (
        data["case_promotion_doctor_preflight_evidence_template_field_count"]
        == DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
    )
    assert (
        data["case_promotion_doctor_preflight_evidence_template_sha256"]
        == DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
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
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "metadata_validation": "Run validate_cases with --packages-dir.",
        "online_smoke": "Run read-only PyPI search smoke.",
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
        "promotion_evidence": _promotion_evidence(
            "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
            "Run read-only PyPI search smoke.",
        ),
        "promotion_evidence_primary_task": {
            "task": "adapter_package",
            "status": "pending",
            "evidence": "",
            "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
            "acceptance_criteria": (
                "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
                "package path or GitHub Release asset name."
            ),
            "priority_rank": 1,
            "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
            "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
            "llm_live_preflight_required": True,
            "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
            "llm_live_preflight_command_sha256": _command_sha256(
                "cliany-site doctor --llm-live --json"
            ),
            "llm_live_preflight_blocker_note": (
                plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
            ),
            "llm_live_preflight_evidence_fields": list(
                plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS
            ),
            "doctor_preflight_evidence_fields": list(
                plan_next_iteration.DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
            ),
            "doctor_preflight_evidence_template": DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
            "doctor_preflight_evidence_selectors": DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS,
            "doctor_preflight_evidence_template_field_count": (
                DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
            ),
            "doctor_preflight_evidence_template_sha256": (
                DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
            ),
        },
        "evidence_bundle_primary_next_task": {
            "task": "adapter_package",
            "status": "pending",
            "evidence": "",
            "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
            "acceptance_criteria": (
                "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
                "package path or GitHub Release asset name."
            ),
            "priority_rank": 1,
            "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
            "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
            "llm_live_preflight_required": True,
            "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
            "llm_live_preflight_command_sha256": _command_sha256(
                "cliany-site doctor --llm-live --json"
            ),
            "llm_live_preflight_blocker_note": (
                plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
            ),
            "llm_live_preflight_evidence_fields": list(
                plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS
            ),
            "doctor_preflight_evidence_fields": list(
                plan_next_iteration.DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
            ),
            "doctor_preflight_evidence_template": DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
            "doctor_preflight_evidence_selectors": DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS,
            "doctor_preflight_evidence_template_field_count": (
                DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
            ),
            "doctor_preflight_evidence_template_sha256": (
                DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
            ),
        },
        "evidence_bundle_primary_next_task_runbook": _pypi_primary_runbook(),
        "candidate_package_validation_command": (
            "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
            "--include-candidate-packages --strict"
        ),
        "promotion_command_plan": _pypi_promotion_command_plan(),
        "promotion_command_plan_summary": _pypi_promotion_command_plan_summary(),
        "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
        "llm_live_preflight_blocker_note": (
            "Run the live LLM preflight before explore. If generate_adapters.ready=false "
            "or llm_live reports warning/error such as E_LLM_UNAVAILABLE "
            "(including provider connection failure), stop candidate promotion, attach "
            "the doctor JSON/error summary, and leave adapter_package pending or blocked."
        ),
        "llm_live_preflight_blocker_comment": LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT,
        "doctor_preflight_blocker_comment": DOCTOR_PREFLIGHT_BLOCKER_COMMENT,
        "doctor_preflight_evidence_fields": DOCTOR_PREFLIGHT_EVIDENCE_FIELDS,
        "doctor_preflight_evidence_template": DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
        "doctor_preflight_evidence_selectors": DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS,
        "doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
        ),
        "llm_live_preflight_evidence_fields": [
            "summary.ready_for_explore",
            "summary.llm_live_preflight",
            "summary.capabilities.generate_adapters.ready",
            "checks[llm_live].status",
            "checks[llm_live].details.error_code",
            "checks[llm_live].details.retryable",
            "checks[llm_live].details.status_code",
            "checks[llm_live].details.phase",
            "checks[llm_live].details.message",
        ],
        "evidence_bundle_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle"
        ),
        "evidence_bundle_json_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle --json"
        ),
        "issue_template_command": (
            "cliany-site cases --case-id pypi-project-search --issue-template"
        ),
        "issue_template_json_command": (
            "cliany-site cases --case-id pypi-project-search --issue-template --json"
        ),
        "issue_body": (
            "## Scope: promote candidate case `pypi-project-search`\n\n"
            "Move this candidate case one step closer to `active` without changing its status early.\n\n"
            "## Primary Evidence Task\n"
            "- Task: `adapter_package`\n"
            "- Status: `pending`\n"
            "- Priority rank: `1`\n"
            "- Priority reason: rank 1: complete 0/3, pending 3, blocked 0, missing commands 0\n"
            "- Current evidence: Not attached yet.\n"
            "- Next action: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "- Acceptance criteria: Attach the generated "
            "<domain>-<version>.cliany-adapter.tar.gz package path or GitHub Release asset name.\n"
            "- Expected adapter package: `pypi.org-<version>.cliany-adapter.tar.gz`\n\n"
            "## Primary Runbook\n"
            "- `llm_live_preflight`: `cliany-site doctor --llm-live --json`\n"
            "  - required: `true`\n"
            "  - handoff: Run the live LLM preflight before explore. "
            "If generate_adapters.ready=false or llm_live reports warning/error such as "
            "E_LLM_UNAVAILABLE (including provider connection failure), stop candidate "
            "promotion, attach the doctor JSON/error summary, and leave adapter_package "
            "pending or blocked.\n"
            '- `adapter_package`: `cliany-site explore "https://pypi.org" "search Python packages" --json`\n'
            "  - required: `true`\n"
            "  - handoff: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "- `acceptance`: `No command.`\n"
            "  - required: `true`\n"
            "  - handoff: Attach the generated "
            "<domain>-<version>.cliany-adapter.tar.gz package path or GitHub Release asset name.\n\n"
            "## Reproduction Context\n"
            "- Target URL: https://pypi.org/search/?q=cliany-site\n"
            "- Candidate commands:\n"
            '  - `cliany-site explore "https://pypi.org" "search Python packages" --json`\n'
            "  - `cliany-site pypi.org search-projects --query cliany-site --limit 5 --json`\n"
            "- Offline validation commands:\n"
            "  - `python scripts/validate_cases.py --strict`\n"
            "  - `python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md`\n\n"
            "## Promotion Command Plan Summary\n"
            "- command_count: `4`\n"
            "- missing_command_count: `0`\n"
            "- all_declared: `true`\n\n"
            "## Promotion Command Plan\n"
            "- `llm_live_preflight`: `cliany-site doctor --llm-live --json`\n"
            f"  - command_sha256: `{_command_sha256(preflight_command)}`\n"
            "  - source: `doctor.llm_live`\n"
            "  - missing: `false`\n"
            '- `adapter_package`: `cliany-site explore "https://pypi.org" "search Python packages" --json`\n'
            f"  - command_sha256: `{_command_sha256(explore_command)}`\n"
            "  - source: `commands.explore`\n"
            "  - missing: `false`\n"
            "- `metadata_validation`: `python scripts/validate_cases.py "
            "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`\n"
            f"  - command_sha256: `{_command_sha256(metadata_command)}`\n"
            "  - source: `candidate_package_validation_command`\n"
            "  - missing: `false`\n"
            "- `online_smoke`: `cliany-site pypi.org search-projects --query cliany-site "
            "--limit 5 --json`\n"
            f"  - command_sha256: `{_command_sha256(smoke_command)}`\n"
            "  - source: `commands.adapter`\n"
            "  - missing: `false`\n\n"
            "## LLM Preflight Gate\n"
            "- Command: `cliany-site doctor --llm-live --json`\n"
            "- Command SHA-256: `0ca644df288169289dd4dbc17aeacdc58b9898f05c0d4c5d304c17e33bdbcb96`\n"
            "- Blocker handling: Run the live LLM preflight before explore. "
            "If generate_adapters.ready=false or llm_live reports warning/error such as "
            "E_LLM_UNAVAILABLE (including provider connection failure), stop candidate "
            "promotion, attach the doctor JSON/error summary, and leave adapter_package "
            "pending or blocked.\n\n"
            "## LLM Preflight Blocker Comment\n"
            f"{LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT}\n\n"
            "## Doctor Preflight Blocker Comment\n"
            f"{DOCTOR_PREFLIGHT_BLOCKER_COMMENT}\n\n"
            "## Doctor Preflight Evidence Fields\n"
            "- `summary.ready_for_explore`\n"
            "- `summary.capabilities.run_browser_workflows.ready`\n"
            "- `summary.capabilities.generate_adapters.ready`\n"
            "- `checks[cdp].status`\n"
            "- `checks[cdp].action`\n"
            "- `checks[llm_live].status`\n"
            "- `checks[llm_live].details.error_code`\n"
            "- `checks[llm_live].details.retryable`\n"
            "- `checks[llm_live].details.phase`\n"
            "- `checks[llm_live].details.message`\n\n"
            "## Doctor Preflight Evidence Template\n"
            "- `summary.ready_for_explore`: `<paste from doctor --llm-live --json>`\n"
            "- `summary.capabilities.run_browser_workflows.ready`: "
            "`<paste from doctor --llm-live --json>`\n"
            "- `summary.capabilities.generate_adapters.ready`: "
            "`<paste from doctor --llm-live --json>`\n"
            "- `checks[cdp].status`: `<paste from doctor --llm-live --json>`\n"
            "- `checks[cdp].action`: `<paste from doctor --llm-live --json>`\n"
            "- `checks[llm_live].status`: `<paste from doctor --llm-live --json>`\n"
            "- `checks[llm_live].details.error_code`: "
            "`<paste from doctor --llm-live --json>`\n"
            "- `checks[llm_live].details.retryable`: "
            "`<paste from doctor --llm-live --json>`\n"
            "- `checks[llm_live].details.phase`: `<paste from doctor --llm-live --json>`\n"
            "- `checks[llm_live].details.message`: `<paste from doctor --llm-live --json>`\n\n"
            "## LLM Preflight Evidence Fields\n"
            "- `summary.ready_for_explore`\n"
            "- `summary.llm_live_preflight`\n"
            "- `summary.capabilities.generate_adapters.ready`\n"
            "- `checks[llm_live].status`\n"
            "- `checks[llm_live].details.error_code`\n"
            "- `checks[llm_live].details.retryable`\n"
            "- `checks[llm_live].details.status_code`\n"
            "- `checks[llm_live].details.phase`\n"
            "- `checks[llm_live].details.message`\n\n"
            "## Acceptance Criteria\n"
            "- `adapter_package`: Attach the generated "
            "<domain>-<version>.cliany-adapter.tar.gz package path or GitHub Release asset name.\n"
            "- `metadata_validation`: Paste `python scripts/validate_cases.py "
            "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict` "
            "output showing the candidate package passed schema v3, manifest hash, "
            "and adapter_domain validation.\n"
            "- `online_smoke`: Paste the read-only adapter command JSON envelope summary "
            "with ok=true, data.quality.ok=true, and row_count>0.\n\n"
            "## Tasks\n"
            "- [ ] `adapter_package`: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "  - Current status: `pending`\n"
            "  - Current evidence: Not attached yet.\n"
            "  - Next action: Generate pypi.org-<version>.cliany-adapter.tar.gz.\n"
            "  - Acceptance criteria: Attach the generated "
            "<domain>-<version>.cliany-adapter.tar.gz package path or GitHub Release asset name.\n"
            "- [ ] `metadata_validation`: Run validate_cases with --packages-dir.\n"
            "  - Current status: `pending`\n"
            "  - Current evidence: Not attached yet.\n"
            "  - Next action: Run validate_cases with --packages-dir.\n"
            "  - Acceptance criteria: Paste `python scripts/validate_cases.py "
            "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict` "
            "output showing the candidate package passed schema v3, manifest hash, "
            "and adapter_domain validation.\n"
            "- [ ] `online_smoke`: Run read-only PyPI search smoke.\n"
            "  - Current status: `pending`\n"
            "  - Current evidence: Not attached yet.\n"
            "  - Next action: Run read-only PyPI search smoke.\n"
            "  - Acceptance criteria: Paste the read-only adapter command JSON envelope summary "
            "with ok=true, data.quality.ok=true, and row_count>0.\n\n"
            "## Evidence Bundle\n"
            "- Human: `cliany-site cases --case-id pypi-project-search --evidence-bundle`\n"
            "- JSON: `cliany-site cases --case-id pypi-project-search --evidence-bundle --json`\n"
            "- Attach or paste the JSON output in the issue once evidence changes.\n\n"
            "## Validation Evidence\n"
            "- Attach the generated `.cliany-adapter.tar.gz` path or release asset name.\n"
            "- Expected adapter package: `pypi.org-<version>.cliany-adapter.tar.gz`\n"
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


def test_plan_passes_remote_audit_args_to_readiness_and_publication(tmp_path, monkeypatch):
    _write_pyproject(tmp_path)
    captured: dict[str, dict[str, object]] = {}

    def fake_build_readiness_report(root: Path, **kwargs: object):
        captured["readiness"] = {"root": root, **kwargs}
        return _readiness_report()

    def fake_build_publication_report(root: Path, **kwargs: object):
        captured["publication"] = {"root": root, **kwargs}
        return _published_publication_report()

    monkeypatch.setattr(plan_next_iteration, "build_readiness_report", fake_build_readiness_report)
    monkeypatch.setattr(plan_next_iteration, "build_publication_report", fake_build_publication_report)

    plan = plan_next_iteration.build_plan(
        tmp_path,
        target_version="0.16.2",
        remote_check=True,
        remote_name="upstream",
    )
    data = plan.to_dict()

    assert captured["readiness"]["root"] == tmp_path
    assert captured["readiness"]["remote_check"] is True
    assert captured["readiness"]["remote_name"] == "upstream"
    assert captured["publication"]["root"] == tmp_path
    assert captured["publication"]["remote_check"] is True
    assert captured["publication"]["remote"] == "upstream"
    assert data["validation_commands"][0] == (
        "python scripts/plan_next_iteration.py --target-version 0.16.2 "
        "--remote --remote-name upstream --json"
    )
    assert data["validation_commands"][1] == (
        "python scripts/release_readiness.py --target-version 0.16.2 "
        "--remote --remote-name upstream --json"
    )
    assert (
        "python scripts/check_release_publication.py --remote --remote-name upstream --json"
        in data["validation_commands"]
    )
    assert data["publication_publish_script_command"] == (
        "python scripts/check_release_publication.py --remote --remote-name upstream "
        "--json --publish-script /tmp/cliany-publish-release.sh"
    )
    assert (
        "python scripts/release_readiness.py --strict --target-version 0.16.2 "
        "--remote --remote-name upstream"
        in data["standard_release_flow"]["commands"]
    )
    assert (
        "python scripts/check_release_publication.py --remote --remote-name upstream "
        "--distribution --json"
        in data["standard_release_flow"]["commands"]
    )
    assert WEBSITE_DEPLOY_COMMAND in data["standard_release_flow"]["commands"]
    assert WEBSITE_INSPECT_COMMAND in data["standard_release_flow"]["commands"]
    assert data["standard_release_flow"]["steps"][-4:] == [
        {
            "name": "target_tag",
            "status": "create_target_tag_at_head",
            "commands": ["git tag v0.16.2", "git push origin v0.16.2"],
        },
        {
            "name": "website_deploy",
            "status": "pending",
            "command": WEBSITE_DEPLOY_COMMAND,
        },
        {
            "name": "website_inspect",
            "status": "pending",
            "command": WEBSITE_INSPECT_COMMAND,
        },
        {
            "name": "remote_publication_audit",
            "status": "pending",
            "command": (
                "python scripts/check_release_publication.py --remote "
                "--remote-name upstream --distribution --json"
            ),
        },
    ]
    standard_release_flow_step_names = [
        step["name"] for step in data["standard_release_flow"]["steps"]
    ]
    assert data["standard_release_flow_step_count"] == len(
        data["standard_release_flow"]["steps"]
    )
    assert data["standard_release_flow_step_names"] == standard_release_flow_step_names
    assert standard_release_flow_step_names.index("website_deploy") < (
        standard_release_flow_step_names.index("website_inspect")
    )
    assert standard_release_flow_step_names.index("website_inspect") < (
        standard_release_flow_step_names.index("remote_publication_audit")
    )
    assert data["standard_release_flow_step_names_sha256"] == _stable_json_sha256(
        standard_release_flow_step_names
    )
    assert data["standard_release_flow_steps_sha256"] == _stable_json_sha256(
        data["standard_release_flow"]["steps"]
    )
    standard_release_flow_step_boundary = {
        "first_step_name": standard_release_flow_step_names[0],
        "last_step_name": standard_release_flow_step_names[-1],
    }
    assert data["standard_release_flow_first_step_name"] == "strict_release_readiness"
    assert data["standard_release_flow_last_step_name"] == "remote_publication_audit"
    assert data["standard_release_flow_step_boundary_sha256"] == _stable_json_sha256(
        standard_release_flow_step_boundary
    )
    standard_release_flow_step_status_counts = (
        _standard_release_flow_step_status_counts(data["standard_release_flow"]["steps"])
    )
    assert data["standard_release_flow_step_status_counts"] == (
        standard_release_flow_step_status_counts
    )
    assert data["standard_release_flow_step_status_counts_sha256"] == _stable_json_sha256(
        standard_release_flow_step_status_counts
    )
    assert data["standard_release_flow_primary_blocked_step_name"] == (
        _standard_release_flow_primary_step_name_with_status_prefix(
            data["standard_release_flow"]["steps"], "blocked"
        )
    )
    primary_blocked_step = next(
        step
        for step in data["standard_release_flow"]["steps"]
        if str(step.get("status")).startswith("blocked")
    )
    assert data["standard_release_flow_primary_blocked_step_command"] == (
        primary_blocked_step["command"]
    )
    assert data["standard_release_flow_primary_blocked_step_status"] == (
        primary_blocked_step["status"]
    )
    assert data["standard_release_flow_primary_blocked_step_status_sha256"] == (
        _stable_json_sha256(primary_blocked_step["status"])
    )
    assert data["standard_release_flow_primary_blocked_step_command_sha256"] == (
        _stable_json_sha256(primary_blocked_step["command"])
    )
    assert data["standard_release_flow_primary_blocked_step_action"] is None
    assert data["standard_release_flow_primary_blocked_step_action_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_name"] == (
        _standard_release_flow_primary_step_name_with_status_prefix(
            data["standard_release_flow"]["steps"], "pending"
        )
    )
    primary_pending_step = next(
        step
        for step in data["standard_release_flow"]["steps"]
        if str(step.get("status")).startswith("pending")
    )
    assert data["standard_release_flow_primary_pending_step_status"] == (
        primary_pending_step["status"]
    )
    assert data["standard_release_flow_primary_pending_step_status_sha256"] == (
        _stable_json_sha256(primary_pending_step["status"])
    )
    assert data["standard_release_flow_primary_pending_step_command"] is None
    assert data["standard_release_flow_primary_pending_step_command_sha256"] is None
    assert data["standard_release_flow_primary_pending_step_action"] == (
        primary_pending_step["action"]
    )
    assert data["standard_release_flow_primary_pending_step_action_sha256"] == (
        _stable_json_sha256(primary_pending_step["action"])
    )
    assert data["standard_release_flow_has_website_deploy"] is True
    assert data["standard_release_flow_website_deploy_command"] == WEBSITE_DEPLOY_COMMAND
    assert data["standard_release_flow_website_deploy_command_sha256"] == (
        _stable_json_sha256(WEBSITE_DEPLOY_COMMAND)
    )
    assert data["standard_release_flow_has_website_inspect"] is True
    assert data["standard_release_flow_website_inspect_command"] == WEBSITE_INSPECT_COMMAND
    assert data["standard_release_flow_website_inspect_command_sha256"] == (
        _stable_json_sha256(WEBSITE_INSPECT_COMMAND)
    )
    distribution_audit_command = (
        "python scripts/check_release_publication.py --remote --remote-name upstream "
        "--distribution --json"
    )
    assert data["standard_release_flow_has_distribution_audit"] is True
    assert (
        data["standard_release_flow_distribution_audit_command"]
        == distribution_audit_command
    )
    assert data["standard_release_flow_distribution_audit_command_sha256"] == (
        _stable_json_sha256(distribution_audit_command)
    )
    publication_handoff = plan_next_iteration._publication_handoff(plan)
    publication_handoff_keys = list(publication_handoff)
    publication_handoff_key_boundary = {
        "first_key": publication_handoff_keys[0],
        "last_key": publication_handoff_keys[-1],
    }
    publication_handoff_key_preview = publication_handoff_keys[:8]
    publication_handoff_key_tail = publication_handoff_keys[-8:]
    assert data["publication_handoff_key_count"] == len(publication_handoff)
    assert data["publication_handoff_schema_version"] == publication_handoff[
        "schema_version"
    ]
    assert data["publication_handoff_first_key"] == publication_handoff_key_boundary[
        "first_key"
    ]
    assert data["publication_handoff_last_key"] == publication_handoff_key_boundary[
        "last_key"
    ]
    assert data["publication_handoff_key_boundary_sha256"] == _stable_json_sha256(
        publication_handoff_key_boundary
    )
    assert data["publication_handoff_key_preview_count"] == len(
        publication_handoff_key_preview
    )
    assert data["publication_handoff_key_preview"] == publication_handoff_key_preview
    assert data["publication_handoff_key_preview_sha256"] == _stable_json_sha256(
        publication_handoff_key_preview
    )
    assert data["publication_handoff_key_tail_count"] == len(publication_handoff_key_tail)
    assert data["publication_handoff_key_tail"] == publication_handoff_key_tail
    assert data["publication_handoff_key_tail_sha256"] == _stable_json_sha256(
        publication_handoff_key_tail
    )
    assert data["publication_handoff_sha256"] == _stable_json_sha256(publication_handoff)
    assert data["publication_handoff_candidate_issue_gate_primary_reason_code"] == (
        publication_handoff["candidate_issue_gate_primary_reason_code"]
    )
    assert data[
        "publication_handoff_candidate_issue_gate_primary_reason_description"
    ] == publication_handoff["candidate_issue_gate_primary_reason_description"]
    assert data[
        "publication_handoff_candidate_issue_gate_primary_required_action"
    ] == publication_handoff["candidate_issue_gate_primary_required_action"]
    release_draft_handoff = plan_next_iteration._release_draft_handoff(plan)
    release_draft_handoff_keys = list(release_draft_handoff)
    release_draft_handoff_key_boundary = {
        "first_key": release_draft_handoff_keys[0],
        "last_key": release_draft_handoff_keys[-1],
    }
    release_draft_handoff_key_preview = release_draft_handoff_keys[:8]
    release_draft_handoff_key_tail = release_draft_handoff_keys[-8:]
    release_draft_required_actions = plan_next_iteration._release_draft_required_actions(
        plan.release_draft_issues
    )
    release_draft_required_action_boundary = {
        "first_action": release_draft_required_actions[0],
        "last_action": release_draft_required_actions[-1],
    }
    release_draft_issue_boundary = {
        "first_issue": plan.release_draft_issues[0],
        "last_issue": plan.release_draft_issues[-1],
    }
    assert data["release_draft_handoff_key_count"] == len(release_draft_handoff)
    assert data["release_draft_handoff_schema_version"] == release_draft_handoff[
        "schema_version"
    ]
    assert data["release_draft_handoff_primary_issue"] == release_draft_handoff[
        "primary_issue"
    ]
    assert data["release_draft_handoff_primary_required_action"] == (
        release_draft_handoff["primary_required_action"]
    )
    assert data["release_draft_handoff_first_key"] == release_draft_handoff_key_boundary[
        "first_key"
    ]
    assert data["release_draft_handoff_last_key"] == release_draft_handoff_key_boundary[
        "last_key"
    ]
    assert data["release_draft_handoff_key_boundary_sha256"] == _stable_json_sha256(
        release_draft_handoff_key_boundary
    )
    assert data["release_draft_handoff_key_preview_count"] == len(
        release_draft_handoff_key_preview
    )
    assert data["release_draft_handoff_key_preview"] == release_draft_handoff_key_preview
    assert data["release_draft_handoff_key_preview_sha256"] == _stable_json_sha256(
        release_draft_handoff_key_preview
    )
    assert data["release_draft_handoff_key_tail_count"] == len(
        release_draft_handoff_key_tail
    )
    assert data["release_draft_handoff_key_tail"] == release_draft_handoff_key_tail
    assert data["release_draft_handoff_key_tail_sha256"] == _stable_json_sha256(
        release_draft_handoff_key_tail
    )
    assert data["release_draft_handoff_sha256"] == _stable_json_sha256(
        release_draft_handoff
    )
    assert data["release_draft_required_action_count"] == len(
        release_draft_required_actions
    )
    assert data["release_draft_required_actions_sha256"] == _stable_json_sha256(
        release_draft_required_actions
    )
    assert data["release_draft_first_required_action"] == (
        release_draft_required_action_boundary["first_action"]
    )
    assert data["release_draft_last_required_action"] == (
        release_draft_required_action_boundary["last_action"]
    )
    assert data["release_draft_required_action_boundary_sha256"] == _stable_json_sha256(
        release_draft_required_action_boundary
    )
    assert data["release_draft_issue_boundary_sha256"] == _stable_json_sha256(
        release_draft_issue_boundary
    )
    assert data["release_draft_issue_preview"] == plan.release_draft_issues[:8]
    assert data["release_draft_issue_tail"] == plan.release_draft_issues[-8:]
    assert (
        "python scripts/check_release_publication.py --remote --remote-name upstream --json"
        in plan_next_iteration._issue_artifact_validation_commands(plan)
    )


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
    assert (
        "Priority Rank | Priority Reason | Promotion Command Plan Summary | "
        "Evidence Bundle Primary Next Task"
    ) in text
    assert (
        "| `pypi-project-search` | Promote candidate case `pypi-project-search` toward active | "
        "`case-proposal`, `good first issue` | `1` | "
        "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0 | "
        "`promotion_command_plan_summary: command_count=4, missing_command_count=0, all_declared=true` | "
        "`adapter_package` |"
    ) in text
    assert "`case-proposal`, `good first issue`" in text
    assert "## Candidate Promotion Tasks" in text
    assert "## Candidate Promotion Evidence Summary" in text
    assert "| candidate_count | `2` |" in text
    assert "| pending_count | `6` |" in text
    assert (
        "| case_promotion_evidence_summary_sha256 | "
        f"`{_stable_json_sha256(plan.case_promotion_evidence_summary)}` |"
    ) in text
    assert (
        "| case_promotion_command_plan_summary_sha256 | "
        f"`{_stable_json_sha256(plan.case_promotion_command_plan_summary)}` |"
    ) in text
    assert "| primary_next_action | `Generate pypi.org-<version>.cliany-adapter.tar.gz.` |" in text
    assert "| case_promotion_evidence_primary_next_task | `{\"case_id\": \"pypi-project-search\"" in text
    assert "\"task\": \"adapter_package\"" in text
    assert (
        "| case_promotion_evidence_primary_next_action | "
        "`Generate pypi.org-<version>.cliany-adapter.tar.gz.` |"
        in text
    )
    assert "| case_promotion_evidence_primary_runbook_step_count | `3` |" in text
    assert (
        "| case_promotion_evidence_primary_runbook_steps | "
        "`[\"llm_live_preflight\", \"adapter_package\", \"acceptance\"]` |"
        in text
    )
    assert (
        "| case_promotion_evidence_primary_runbook_steps_sha256 | "
        f"`{_stable_json_sha256(['llm_live_preflight', 'adapter_package', 'acceptance'])}` |"
        in text
    )
    assert "| case_promotion_llm_live_preflight_evidence_field_count | `9` |" in text
    assert (
        "| case_promotion_llm_live_preflight_evidence_fields_sha256 | "
        f"`{_stable_json_sha256(list(plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS))}` |"
        in text
    )
    assert "summary.llm_live_preflight" in text
    standard_release_flow_step_names = [
        step["name"] for step in plan.standard_release_flow["steps"]
    ]
    standard_release_flow_step_boundary = {
        "first_step_name": standard_release_flow_step_names[0],
        "last_step_name": standard_release_flow_step_names[-1],
    }
    assert f"| standard_release_flow_step_count | `{len(plan.standard_release_flow['steps'])}` |" in text
    assert (
        "| standard_release_flow_step_names | "
        f"`{json.dumps(standard_release_flow_step_names, ensure_ascii=False)}` |"
        in text
    )
    assert (
        "| standard_release_flow_step_names_sha256 | "
        f"`{_stable_json_sha256(standard_release_flow_step_names)}` |"
        in text
    )
    assert (
        "| standard_release_flow_steps_sha256 | "
        f"`{_stable_json_sha256(plan.standard_release_flow['steps'])}` |"
        in text
    )
    assert "| standard_release_flow_first_step_name | `strict_release_readiness` |" in text
    assert "| standard_release_flow_last_step_name | `remote_publication_audit` |" in text
    assert (
        "| standard_release_flow_step_boundary_sha256 | "
        f"`{_stable_json_sha256(standard_release_flow_step_boundary)}` |"
        in text
    )
    standard_release_flow_step_status_counts = (
        _standard_release_flow_step_status_counts(plan.standard_release_flow["steps"])
    )
    assert (
        "| standard_release_flow_step_status_counts | "
        f"`{json.dumps(standard_release_flow_step_status_counts, ensure_ascii=False)}` |"
        in text
    )
    assert (
        "| standard_release_flow_step_status_counts_sha256 | "
        f"`{_stable_json_sha256(standard_release_flow_step_status_counts)}` |"
        in text
    )
    standard_release_flow_primary_blocked_step_name = (
        _standard_release_flow_primary_step_name_with_status_prefix(
            plan.standard_release_flow["steps"], "blocked"
        )
    )
    assert (
        "| standard_release_flow_primary_blocked_step_name | `"
        f"{standard_release_flow_primary_blocked_step_name}` |"
        in text
    )
    primary_blocked_step = next(
        step
        for step in plan.standard_release_flow["steps"]
        if str(step.get("status")).startswith("blocked")
    )
    assert (
        "| standard_release_flow_primary_blocked_step_status | `"
        f"{primary_blocked_step['status']}` |"
        in text
    )
    assert (
        "| standard_release_flow_primary_blocked_step_status_sha256 | `"
        f"{_stable_json_sha256(primary_blocked_step['status'])}` |"
        in text
    )
    assert (
        "| standard_release_flow_primary_blocked_step_command | `"
        f"{primary_blocked_step['command']}` |"
        in text
    )
    assert (
        "| standard_release_flow_primary_blocked_step_command_sha256 | `"
        f"{_stable_json_sha256(primary_blocked_step['command'])}` |"
        in text
    )
    assert "| standard_release_flow_primary_blocked_step_action | `(none)` |" in text
    assert (
        "| standard_release_flow_primary_blocked_step_action_sha256 | `(none)` |"
        in text
    )
    assert "| standard_release_flow_primary_pending_step_name | `release_notes` |" in text
    primary_pending_step = next(
        step
        for step in plan.standard_release_flow["steps"]
        if str(step.get("status")).startswith("pending")
    )
    assert (
        "| standard_release_flow_primary_pending_step_status | `"
        f"{primary_pending_step['status']}` |"
        in text
    )
    assert (
        "| standard_release_flow_primary_pending_step_status_sha256 | `"
        f"{_stable_json_sha256(primary_pending_step['status'])}` |"
        in text
    )
    assert "| standard_release_flow_primary_pending_step_command | `(none)` |" in text
    assert (
        "| standard_release_flow_primary_pending_step_command_sha256 | `(none)` |"
        in text
    )
    assert (
        "| standard_release_flow_primary_pending_step_action | `"
        f"{primary_pending_step['action']}` |"
        in text
    )
    assert (
        "| standard_release_flow_primary_pending_step_action_sha256 | `"
        f"{_stable_json_sha256(primary_pending_step['action'])}` |"
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
    assert "| publication_blocker_count | `3` |" in text
    assert (
        "| publication_blockers_sha256 | "
        f"`{_stable_json_sha256(plan.publication_blockers)}` |"
    ) in text
    assert "| publication_primary_blocker | `publication worktree is dirty` |" in text
    assert "## Publication Blockers" in text
    assert "- publication worktree is dirty" in text
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
    publication_handoff = plan_next_iteration._publication_handoff(plan)
    publication_handoff_keys = list(publication_handoff)
    publication_handoff_key_boundary = {
        "first_key": publication_handoff_keys[0],
        "last_key": publication_handoff_keys[-1],
    }
    assert f"| publication_handoff_key_count | `{len(publication_handoff)}` |" in text
    assert "| publication_handoff_schema_version | `1` |" in text
    assert (
        "| publication_handoff_first_key | "
        f"`{publication_handoff_key_boundary['first_key']}` |"
        in text
    )
    assert (
        "| publication_handoff_last_key | "
        f"`{publication_handoff_key_boundary['last_key']}` |"
        in text
    )
    assert (
        "| publication_handoff_key_boundary_sha256 | "
        f"`{_stable_json_sha256(publication_handoff_key_boundary)}` |"
        in text
    )
    assert (
        "| publication_handoff_sha256 | "
        f"`{_stable_json_sha256(publication_handoff)}` |"
        in text
    )
    release_draft_handoff = plan_next_iteration._release_draft_handoff(plan)
    release_draft_handoff_keys = list(release_draft_handoff)
    release_draft_handoff_key_boundary = {
        "first_key": release_draft_handoff_keys[0],
        "last_key": release_draft_handoff_keys[-1],
    }
    release_draft_required_actions = plan_next_iteration._release_draft_required_actions(
        plan.release_draft_issues
    )
    release_draft_required_action_boundary = {
        "first_action": release_draft_required_actions[0],
        "last_action": release_draft_required_actions[-1],
    }
    assert f"| release_draft_handoff_key_count | `{len(release_draft_handoff)}` |" in text
    assert "| release_draft_handoff_schema_version | `1` |" in text
    assert (
        "| release_draft_handoff_first_key | "
        f"`{release_draft_handoff_key_boundary['first_key']}` |"
        in text
    )
    assert (
        "| release_draft_handoff_last_key | "
        f"`{release_draft_handoff_key_boundary['last_key']}` |"
        in text
    )
    assert (
        "| release_draft_handoff_key_boundary_sha256 | "
        f"`{_stable_json_sha256(release_draft_handoff_key_boundary)}` |"
        in text
    )
    assert (
        "| release_draft_handoff_sha256 | "
        f"`{_stable_json_sha256(release_draft_handoff)}` |"
        in text
    )
    assert (
        "| release_draft_required_action_count | "
        f"`{len(release_draft_required_actions)}` |"
        in text
    )
    assert (
        "| release_draft_required_action_boundary_sha256 | "
        f"`{_stable_json_sha256(release_draft_required_action_boundary)}` |"
        in text
    )
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
    assert (
        "case_promotion_evidence_primary_runbook_steps: "
        "llm_live_preflight -> adapter_package -> acceptance"
        in text
    )
    assert (
        "case_promotion_evidence_primary_runbook_steps_sha256: "
        f"{_stable_json_sha256(['llm_live_preflight', 'adapter_package', 'acceptance'])}"
        in text
    )
    assert (
        "case_promotion_evidence_summary_sha256: "
        f"{_stable_json_sha256(plan.case_promotion_evidence_summary)}"
        in text
    )
    assert (
        "case_promotion_command_plan_summary_sha256: "
        f"{_stable_json_sha256(plan.case_promotion_command_plan_summary)}"
        in text
    )
    assert "candidate_promotions:" in text
    assert "  evidence_bundle_primary_next_task:" in text
    assert "    task: adapter_package" in text
    assert "candidate_issue_gate:" in text
    assert "publication_blocker_count: 3" in text
    assert f"publication_blockers_sha256: {_stable_json_sha256(plan.publication_blockers)}" in text
    assert "publication_primary_blocker: publication worktree is dirty" in text
    assert "publication_blockers:" in text
    assert "publication_next_action_count: 3" in text
    assert f"publication_next_actions_sha256: {_stable_json_sha256(plan.publication_next_actions)}" in text
    assert (
        "publication_primary_next_action: "
        "Commit, stash, or discard local worktree changes before publishing release refs."
        in text
    )
    publication_handoff = plan_next_iteration._publication_handoff(plan)
    publication_handoff_keys = list(publication_handoff)
    publication_handoff_key_boundary = {
        "first_key": publication_handoff_keys[0],
        "last_key": publication_handoff_keys[-1],
    }
    assert f"publication_handoff_key_count: {len(publication_handoff)}" in text
    assert "publication_handoff_schema_version: 1" in text
    assert (
        f"publication_handoff_first_key: {publication_handoff_key_boundary['first_key']}"
        in text
    )
    assert (
        f"publication_handoff_last_key: {publication_handoff_key_boundary['last_key']}"
        in text
    )
    assert (
        "publication_handoff_key_boundary_sha256: "
        f"{_stable_json_sha256(publication_handoff_key_boundary)}"
        in text
    )
    assert (
        "publication_handoff_sha256: "
        f"{_stable_json_sha256(publication_handoff)}"
        in text
    )
    release_draft_handoff = plan_next_iteration._release_draft_handoff(plan)
    release_draft_handoff_keys = list(release_draft_handoff)
    release_draft_handoff_key_boundary = {
        "first_key": release_draft_handoff_keys[0],
        "last_key": release_draft_handoff_keys[-1],
    }
    release_draft_required_actions = plan_next_iteration._release_draft_required_actions(
        plan.release_draft_issues
    )
    release_draft_required_action_boundary = {
        "first_action": release_draft_required_actions[0],
        "last_action": release_draft_required_actions[-1],
    }
    assert f"release_draft_handoff_key_count: {len(release_draft_handoff)}" in text
    assert "release_draft_handoff_schema_version: 1" in text
    assert (
        f"release_draft_handoff_first_key: {release_draft_handoff_key_boundary['first_key']}"
        in text
    )
    assert (
        f"release_draft_handoff_last_key: {release_draft_handoff_key_boundary['last_key']}"
        in text
    )
    assert (
        "release_draft_handoff_key_boundary_sha256: "
        f"{_stable_json_sha256(release_draft_handoff_key_boundary)}"
        in text
    )
    assert (
        "release_draft_handoff_sha256: "
        f"{_stable_json_sha256(release_draft_handoff)}"
        in text
    )
    assert (
        f"release_draft_required_action_count: {len(release_draft_required_actions)}"
        in text
    )
    assert (
        "release_draft_required_action_boundary_sha256: "
        f"{_stable_json_sha256(release_draft_required_action_boundary)}"
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
    planner_handoff = json.loads((issues_dir / "planner-handoff.json").read_text(encoding="utf-8"))
    publication_handoff = json.loads((issues_dir / "publication-handoff.json").read_text(encoding="utf-8"))
    release_draft_handoff = json.loads((issues_dir / "release-draft-handoff.json").read_text(encoding="utf-8"))
    script = (issues_dir / "create-issues.sh").read_text(encoding="utf-8")
    readme = (issues_dir / "README.md").read_text(encoding="utf-8")
    llm_preflight_fields = list(plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS)
    promotion_summaries = {
        promotion.case_id: promotion.promotion_command_plan_summary
        for promotion in plan.candidate_promotions
    }
    issue_body_inventory = []
    for body_name in ("pypi-project-search.md", "npm-package-search.md"):
        body_bytes = (issues_dir / body_name).read_bytes()
        case_id = body_name.removesuffix(".md")
        issue_body_inventory.append(
            {
                "case_id": case_id,
                "issue_body_name": body_name,
                "byte_count": len(body_bytes),
                "sha256": hashlib.sha256(body_bytes).hexdigest(),
                "promotion_command_plan_summary": promotion_summaries[case_id],
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
            "priority_rank": item["priority_rank"],
            "priority_reason": item["priority_reason"],
            "promotion_evidence": item["promotion_evidence"],
            "promotion_evidence_primary_task": item["promotion_evidence_primary_task"],
            "evidence_bundle_primary_next_task": item["evidence_bundle_primary_next_task"],
            "evidence_bundle_primary_next_task_runbook": item[
                "evidence_bundle_primary_next_task_runbook"
            ],
            "candidate_package_validation_command": item["candidate_package_validation_command"],
            "promotion_command_plan": item["promotion_command_plan"],
            "promotion_command_plan_summary": item["promotion_command_plan_summary"],
            "llm_live_preflight_command": item["llm_live_preflight_command"],
            "llm_live_preflight_blocker_note": item["llm_live_preflight_blocker_note"],
            "llm_live_preflight_evidence_fields": item[
                "llm_live_preflight_evidence_fields"
            ],
            "doctor_preflight_evidence_fields": item[
                "doctor_preflight_evidence_fields"
            ],
            "doctor_preflight_evidence_template": item[
                "doctor_preflight_evidence_template"
            ],
            "doctor_preflight_evidence_template_field_count": item[
                "doctor_preflight_evidence_template_field_count"
            ],
            "doctor_preflight_evidence_template_sha256": item[
                "doctor_preflight_evidence_template_sha256"
            ],
            "issue_template_command": item["issue_template_command"],
            "issue_template_json_command": item["issue_template_json_command"],
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
        "target_tag": "v0.16.2",
        "target_tag_matches_latest": False,
        "target_tag_status": "blocked_by_worktree",
        "target_tag_required_action": (
            "Commit, stash, or discard local worktree changes before creating target tag "
            "`v0.16.2`."
        ),
        "target_tag_command_count": 2,
        "target_tag_commands_sha256": _stable_json_sha256(
            ["git tag v0.16.2", "git push origin v0.16.2"]
        ),
        "target_tag_primary_command": "git tag v0.16.2",
        "target_tag_commands": ["git tag v0.16.2", "git push origin v0.16.2"],
        **_target_tag_release_gate_fields(),
    }
    expected_publication_blockers = [
        "publication worktree is dirty",
        "latest local release is not published",
        "latest local release tag is not published",
    ]
    standard_release_flow_steps = plan.standard_release_flow["steps"]
    standard_release_flow_step_names = [
        step["name"] for step in standard_release_flow_steps
    ]
    standard_release_flow_step_boundary = {
        "first_step_name": standard_release_flow_step_names[0],
        "last_step_name": standard_release_flow_step_names[-1],
    }
    standard_release_flow_step_status_counts = (
        _standard_release_flow_step_status_counts(standard_release_flow_steps)
    )
    primary_blocked_step = next(
        step
        for step in standard_release_flow_steps
        if str(step.get("status")).startswith("blocked")
    )
    primary_pending_step = next(
        step
        for step in standard_release_flow_steps
        if str(step.get("status")).startswith("pending")
    )
    primary_blocked_command = primary_blocked_step.get("command")
    primary_blocked_status = primary_blocked_step.get("status")
    primary_blocked_action = primary_blocked_step.get("action")
    primary_pending_command = primary_pending_step.get("command")
    primary_pending_status = primary_pending_step.get("status")
    primary_pending_action = primary_pending_step.get("action")
    expected_standard_release_flow_primary_step_handoff_aliases = {
        "standard_release_flow_primary_blocked_step_name": primary_blocked_step.get(
            "name"
        ),
        "standard_release_flow_primary_blocked_step_status": primary_blocked_status,
        "standard_release_flow_primary_blocked_step_status_sha256": (
            _stable_json_sha256(primary_blocked_status)
            if primary_blocked_status
            else None
        ),
        "standard_release_flow_primary_blocked_step_command": primary_blocked_command,
        "standard_release_flow_primary_blocked_step_command_sha256": (
            _stable_json_sha256(primary_blocked_command)
            if primary_blocked_command
            else None
        ),
        "standard_release_flow_primary_blocked_step_action": primary_blocked_action,
        "standard_release_flow_primary_blocked_step_action_sha256": (
            _stable_json_sha256(primary_blocked_action)
            if primary_blocked_action
            else None
        ),
        "standard_release_flow_primary_pending_step_name": primary_pending_step.get(
            "name"
        ),
        "standard_release_flow_primary_pending_step_status": primary_pending_status,
        "standard_release_flow_primary_pending_step_status_sha256": (
            _stable_json_sha256(primary_pending_status)
            if primary_pending_status
            else None
        ),
        "standard_release_flow_primary_pending_step_command": primary_pending_command,
        "standard_release_flow_primary_pending_step_command_sha256": (
            _stable_json_sha256(primary_pending_command)
            if primary_pending_command
            else None
        ),
        "standard_release_flow_primary_pending_step_action": primary_pending_action,
        "standard_release_flow_primary_pending_step_action_sha256": (
            _stable_json_sha256(primary_pending_action)
            if primary_pending_action
            else None
        ),
    }
    expected_publication_handoff = {
        "schema_version": 1,
        "publication_ok": False,
        "daily_release_cap_blocked": False,
        "daily_release_resume_date": None,
        "daily_release_resume_date_sha256": None,
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
        "publication_blocker_count": len(expected_publication_blockers),
        "publication_blockers_sha256": _stable_json_sha256(expected_publication_blockers),
        "publication_primary_blocker": "publication worktree is dirty",
        "publication_blockers": expected_publication_blockers,
        "next_actions": plan.next_actions,
        "commit_cadence": plan.commit_cadence,
        "commit_cadence_status": "needs_more_commit_days",
        "commit_cadence_missing_commit_days": 1,
        "commit_cadence_primary_next_action": (
            "Ship verified slices on `1` more unique commit days this week."
        ),
        "standard_release_flow": plan.standard_release_flow,
        "standard_release_flow_status": plan.standard_release_flow["status"],
        "standard_release_flow_primary_next_action": plan.standard_release_flow[
            "primary_next_action"
        ],
        "standard_release_flow_command_count": plan.standard_release_flow["command_count"],
        "standard_release_flow_commands_sha256": plan.standard_release_flow[
            "commands_sha256"
        ],
        "standard_release_flow_step_count": len(standard_release_flow_steps),
        "standard_release_flow_step_names": standard_release_flow_step_names,
        "standard_release_flow_step_names_sha256": _stable_json_sha256(
            standard_release_flow_step_names
        ),
        "standard_release_flow_steps_sha256": _stable_json_sha256(
            standard_release_flow_steps
        ),
        "standard_release_flow_first_step_name": "strict_release_readiness",
        "standard_release_flow_last_step_name": "remote_publication_audit",
        "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
            standard_release_flow_step_boundary
        ),
        "standard_release_flow_step_status_counts": standard_release_flow_step_status_counts,
        "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
            standard_release_flow_step_status_counts
        ),
        **expected_standard_release_flow_primary_step_handoff_aliases,
        "standard_release_flow_has_website_deploy": True,
        "standard_release_flow_website_deploy_command": WEBSITE_DEPLOY_COMMAND,
        "standard_release_flow_website_deploy_command_sha256": _stable_json_sha256(
            WEBSITE_DEPLOY_COMMAND
        ),
        "standard_release_flow_has_website_inspect": True,
        "standard_release_flow_website_inspect_command": WEBSITE_INSPECT_COMMAND,
        "standard_release_flow_website_inspect_command_sha256": _stable_json_sha256(
            WEBSITE_INSPECT_COMMAND
        ),
        "standard_release_flow_has_distribution_audit": True,
        "standard_release_flow_distribution_audit_command": DISTRIBUTION_AUDIT_COMMAND,
        "standard_release_flow_distribution_audit_command_sha256": _stable_json_sha256(
            DISTRIBUTION_AUDIT_COMMAND
        ),
        "standard_release_flow_sha256": _stable_json_sha256(plan.standard_release_flow),
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
        "planner_handoff": "planner-handoff.json",
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
            "promotion_command_plan, llm_live_preflight_required, "
            "llm_live_preflight_command, llm_live_preflight_blocker_note, and "
            "llm_live_preflight_evidence_fields / doctor_preflight_evidence_fields "
            "for each case."
        ),
        "Review each body file for scope, tasks, validation evidence, and non-goals.",
        (
            "If candidate_issue_gate.requires_maintainer_review is true, set "
            "CLIANY_CREATE_ISSUES_ACK_REVIEW=1 only after completing that review."
        ),
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
        "preflight_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 --json"
        ),
        "preflight_json": "/tmp/cliany-issue-gate-check.json",
        "maintainer_review_ack_env": "CLIANY_CREATE_ISSUES_ACK_REVIEW=1",
        "maintainer_review_ack_required_when": (
            "candidate_issue_gate.requires_maintainer_review=true"
        ),
    }
    create_issues_safety_contract_keys = list(expected_create_issues_safety_contract)
    review_order = [
        "README.md",
        "planner-handoff.json",
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
        "preflight_command": (
            "python scripts/plan_next_iteration.py --target-version 0.16.2 --json"
        ),
        "preflight_json": "/tmp/cliany-issue-gate-check.json",
        "maintainer_review_ack_env": "CLIANY_CREATE_ISSUES_ACK_REVIEW=1",
        "maintainer_review_ack_required_when": (
            "candidate_issue_gate.requires_maintainer_review=true"
        ),
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
        "daily_release_cap_blocked": False,
        "daily_release_resume_date": None,
        "daily_release_resume_date_sha256": None,
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
        "case_promotion_evidence_primary_expected_adapter_package": (
            "pypi.org-<version>.cliany-adapter.tar.gz"
        ),
        "case_promotion_evidence_primary_acceptance_criteria": (
            plan_next_iteration.CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA["adapter_package"]
        ),
        "case_promotion_evidence_primary_acceptance_criteria_sha256": (
            _stable_json_sha256(
                plan_next_iteration.CANDIDATE_PROMOTION_ACCEPTANCE_CRITERIA[
                    "adapter_package"
                ]
            )
        ),
        "case_promotion_evidence_primary_priority_rank": 1,
        "case_promotion_evidence_primary_priority_reason": (
            "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0"
        ),
        "case_promotion_evidence_primary_issue_template_command": (
            "cliany-site cases --case-id pypi-project-search --issue-template"
        ),
        "case_promotion_evidence_primary_issue_template_json_command": (
            "cliany-site cases --case-id pypi-project-search --issue-template --json"
        ),
        "case_promotion_evidence_primary_evidence_bundle_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle"
        ),
        "case_promotion_evidence_primary_evidence_bundle_json_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle --json"
        ),
        "case_promotion_evidence_primary_evidence_sha256": _stable_json_sha256(""),
        "case_promotion_evidence_primary_detail_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary["primary_task_detail"]
        ),
        "case_promotion_evidence_primary_next_task_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary["primary_next_task"]
        ),
        "case_promotion_evidence_primary_runbook_step_count": 3,
        "case_promotion_evidence_primary_runbook_steps": [
            "llm_live_preflight",
            "adapter_package",
            "acceptance",
        ],
        "case_promotion_evidence_primary_runbook_steps_sha256": _stable_json_sha256(
            ["llm_live_preflight", "adapter_package", "acceptance"]
        ),
        "case_promotion_evidence_primary_runbook_first_step": "llm_live_preflight",
        "case_promotion_evidence_primary_runbook_first_command": (
            "cliany-site doctor --llm-live --json"
        ),
        "case_promotion_evidence_primary_runbook_first_command_sha256": _command_sha256(
            "cliany-site doctor --llm-live --json"
        ),
        "case_promotion_evidence_primary_runbook_sha256": _stable_json_sha256(
            plan.case_promotion_evidence_summary["primary_next_task_runbook"]
        ),
        "case_promotion_evidence_primary_llm_live_preflight_required": True,
        "case_promotion_evidence_primary_llm_live_preflight_command": (
            "cliany-site doctor --llm-live --json"
        ),
        "case_promotion_evidence_primary_llm_live_preflight_command_sha256": (
            _command_sha256("cliany-site doctor --llm-live --json")
        ),
        "case_promotion_evidence_primary_llm_live_preflight_blocker_note": (
            plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
        ),
        "case_promotion_evidence_primary_llm_live_preflight_blocker_comment": (
            LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT
        ),
        "case_promotion_evidence_primary_doctor_preflight_blocker_comment": (
            DOCTOR_PREFLIGHT_BLOCKER_COMMENT
        ),
        "case_promotion_evidence_primary_doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "case_promotion_evidence_primary_doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
        ),
        "case_promotion_llm_live_preflight_evidence_field_count": len(
            llm_preflight_fields
        ),
        "case_promotion_llm_live_preflight_evidence_fields": llm_preflight_fields,
        "case_promotion_llm_live_preflight_evidence_fields_sha256": _stable_json_sha256(
            llm_preflight_fields
        ),
        "case_promotion_doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "case_promotion_doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
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
        "standard_release_flow_status": plan.standard_release_flow["status"],
        "standard_release_flow_target_tag": plan.standard_release_flow["target_tag"],
        "standard_release_flow_primary_next_action": plan.standard_release_flow[
            "primary_next_action"
        ],
        "standard_release_flow_command_count": plan.standard_release_flow["command_count"],
        "standard_release_flow_commands_sha256": plan.standard_release_flow[
            "commands_sha256"
        ],
        "standard_release_flow_step_count": len(standard_release_flow_steps),
        "standard_release_flow_step_names": standard_release_flow_step_names,
        "standard_release_flow_step_names_sha256": _stable_json_sha256(
            standard_release_flow_step_names
        ),
        "standard_release_flow_steps_sha256": _stable_json_sha256(
            standard_release_flow_steps
        ),
        "standard_release_flow_first_step_name": "strict_release_readiness",
        "standard_release_flow_last_step_name": "remote_publication_audit",
        "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
            standard_release_flow_step_boundary
        ),
        "standard_release_flow_step_status_counts": standard_release_flow_step_status_counts,
        "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
            standard_release_flow_step_status_counts
        ),
        **expected_standard_release_flow_primary_step_handoff_aliases,
        "standard_release_flow_has_website_deploy": True,
        "standard_release_flow_website_deploy_command": WEBSITE_DEPLOY_COMMAND,
        "standard_release_flow_website_deploy_command_sha256": _stable_json_sha256(
            WEBSITE_DEPLOY_COMMAND
        ),
        "standard_release_flow_has_website_inspect": True,
        "standard_release_flow_website_inspect_command": WEBSITE_INSPECT_COMMAND,
        "standard_release_flow_website_inspect_command_sha256": _stable_json_sha256(
            WEBSITE_INSPECT_COMMAND
        ),
        "standard_release_flow_has_distribution_audit": True,
        "standard_release_flow_distribution_audit_command": DISTRIBUTION_AUDIT_COMMAND,
        "standard_release_flow_distribution_audit_command_sha256": _stable_json_sha256(
            DISTRIBUTION_AUDIT_COMMAND
        ),
        "standard_release_flow_sha256": _stable_json_sha256(plan.standard_release_flow),
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
        "publication_target_tag": expected_tag_publish_decision["target_tag"],
        "publication_target_tag_status": expected_tag_publish_decision[
            "target_tag_status"
        ],
        "publication_target_tag_primary_command": expected_tag_publish_decision[
            "target_tag_primary_command"
        ],
        "publication_target_tag_command_count": expected_tag_publish_decision[
            "target_tag_command_count"
        ],
        "publication_target_tag_commands_sha256": expected_tag_publish_decision[
            "target_tag_commands_sha256"
        ],
        "publication_target_tag_required_action_sha256": _stable_json_sha256(
            expected_tag_publish_decision["target_tag_required_action"]
        ),
        "publication_target_tag_release_gate_status": expected_tag_publish_decision[
            "target_tag_release_gate_status"
        ],
        "publication_target_tag_release_gate_blocker_count": expected_tag_publish_decision[
            "target_tag_release_gate_blocker_count"
        ],
        "publication_target_tag_release_gate_primary_blocker": expected_tag_publish_decision[
            "target_tag_release_gate_primary_blocker"
        ],
        "publication_target_tag_release_gate_required_action_sha256": _stable_json_sha256(
            expected_tag_publish_decision["target_tag_release_gate_required_action"]
        ),
        "publication_target_tag_release_gate_blockers_sha256": expected_tag_publish_decision[
            "target_tag_release_gate_blockers_sha256"
        ],
        "publication_blocker_count": len(expected_publication_blockers),
        "publication_blockers_sha256": _stable_json_sha256(expected_publication_blockers),
        "publication_primary_blocker": expected_publication_blockers[0],
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
        "commit_cadence_release_count_today": 0,
        "commit_cadence_max_daily_releases": 3,
        "commit_cadence_daily_release_limit_ok": True,
        "commit_cadence_next_action_count": 1,
        "commit_cadence_primary_next_action": (
            "Ship verified slices on `1` more unique commit days this week."
        ),
        "commit_cadence_commit_days_sha256": _stable_json_sha256([]),
        "commit_cadence_release_tags_today_sha256": _stable_json_sha256([]),
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
        "review_checklist_count": 8,
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
        "create_issues_safety_contract_key_count": 7,
        "create_issues_safety_contract_sha256": _stable_json_sha256(
            expected_create_issues_safety_contract
        ),
        "create_issues_safety_contract_first_key": "dry_run_supported",
        "create_issues_safety_contract_last_key": "maintainer_review_ack_required_when",
        "create_issues_safety_contract_key_boundary_sha256": _stable_json_sha256(
            {
                "first_key": "dry_run_supported",
                "last_key": "maintainer_review_ack_required_when",
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
    assert "## Promotion Command Plan Summary" in body
    assert "- command_count: `4`" in body
    assert "- missing_command_count: `0`" in body
    assert "- all_declared: `true`" in body
    assert "## Promotion Command Plan" in body
    assert (
        f"  - command_sha256: `{_command_sha256('cliany-site doctor --llm-live --json')}`"
        in body
    )
    assert "  - source: `doctor.llm_live`" in body
    assert "  - missing: `false`" in body
    assert (
        "  - command_sha256: "
        f"`{_command_sha256('cliany-site pypi.org search-projects --query cliany-site --limit 5 --json')}`"
        in body
    )
    assert "  - source: `commands.adapter`" in body
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
    assert metadata[0]["priority_rank"] == 1
    assert metadata[0]["priority_reason"] == (
        "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0"
    )
    assert metadata[0]["promotion_evidence"] == _promotion_evidence(
        "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        "Run read-only PyPI search smoke.",
    )
    assert metadata[0]["promotion_evidence_primary_task"] == {
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        "acceptance_criteria": (
            "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
            "package path or GitHub Release asset name."
        ),
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "llm_live_preflight_required": True,
        "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
        "llm_live_preflight_command_sha256": _command_sha256(
            "cliany-site doctor --llm-live --json"
        ),
        "llm_live_preflight_blocker_note": (
            plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
        ),
        "llm_live_preflight_evidence_fields": list(
            plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS
        ),
        "doctor_preflight_evidence_fields": list(
            plan_next_iteration.DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
        ),
        "doctor_preflight_evidence_template": DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
        "doctor_preflight_evidence_selectors": DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS,
        "doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
        ),
    }
    assert metadata[0]["evidence_bundle_primary_next_task"] == {
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": "Generate pypi.org-<version>.cliany-adapter.tar.gz.",
        "acceptance_criteria": (
            "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
            "package path or GitHub Release asset name."
        ),
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "llm_live_preflight_required": True,
        "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
        "llm_live_preflight_command_sha256": _command_sha256(
            "cliany-site doctor --llm-live --json"
        ),
        "llm_live_preflight_blocker_note": (
            plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE
        ),
        "llm_live_preflight_evidence_fields": list(
            plan_next_iteration.LLM_LIVE_PREFLIGHT_EVIDENCE_FIELDS
        ),
        "doctor_preflight_evidence_fields": list(
            plan_next_iteration.DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
        ),
        "doctor_preflight_evidence_template": DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE,
        "doctor_preflight_evidence_selectors": DOCTOR_PREFLIGHT_EVIDENCE_SELECTORS,
        "doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
        ),
    }
    assert metadata[0]["evidence_bundle_primary_next_task_runbook"] == _pypi_primary_runbook()
    assert metadata[0]["candidate_package_validation_command"] == (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
    )
    assert metadata[0]["promotion_command_plan"] == _pypi_promotion_command_plan()
    assert metadata[0]["promotion_command_plan_summary"] == (
        _pypi_promotion_command_plan_summary()
    )
    assert metadata[0]["llm_live_preflight_command"] == "cliany-site doctor --llm-live --json"
    assert "E_LLM_UNAVAILABLE" in metadata[0]["llm_live_preflight_blocker_note"]
    assert "provider connection failure" in metadata[0]["llm_live_preflight_blocker_note"]
    assert metadata[0]["llm_live_preflight_evidence_fields"] == [
        "summary.ready_for_explore",
        "summary.llm_live_preflight",
        "summary.capabilities.generate_adapters.ready",
        "checks[llm_live].status",
        "checks[llm_live].details.error_code",
        "checks[llm_live].details.retryable",
        "checks[llm_live].details.status_code",
        "checks[llm_live].details.phase",
        "checks[llm_live].details.message",
    ]
    assert metadata[0]["doctor_preflight_evidence_fields"] == DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
    assert metadata[0]["doctor_preflight_evidence_template"] == (
        DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE
    )
    assert (
        metadata[0]["doctor_preflight_evidence_template_field_count"]
        == DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
    )
    assert (
        metadata[0]["doctor_preflight_evidence_template_sha256"]
        == DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
    )
    assert (
        metadata[0]["issue_template_command"]
        == "cliany-site cases --case-id pypi-project-search --issue-template"
    )
    assert (
        metadata[0]["issue_template_json_command"]
        == "cliany-site cases --case-id pypi-project-search --issue-template --json"
    )
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
    assert artifact_manifest["standard_release_flow"]["steps"][-3:] == [
        {
            "name": "website_deploy",
            "status": "pending",
            "command": WEBSITE_DEPLOY_COMMAND,
        },
        {
            "name": "website_inspect",
            "status": "pending",
            "command": WEBSITE_INSPECT_COMMAND,
        },
        {
            "name": "remote_publication_audit",
            "status": "pending",
            "command": DISTRIBUTION_AUDIT_COMMAND,
        },
    ]
    assert artifact_manifest == {
        "schema_version": plan_next_iteration.ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "target_version": "0.16.2",
        "artifact_bundle_summary": artifact_bundle_summary,
        "daily_release_cap_blocked": False,
        "daily_release_resume_date": None,
        "daily_release_resume_date_sha256": None,
        "candidate_count": 2,
        "candidate_cases": ["pypi-project-search", "npm-package-search"],
        "case_promotion_evidence_summary": plan.case_promotion_evidence_summary,
        "case_promotion_llm_live_preflight_evidence_fields": llm_preflight_fields,
        "case_promotion_llm_live_preflight_evidence_field_count": len(
            llm_preflight_fields
        ),
        "case_promotion_llm_live_preflight_evidence_fields_sha256": _stable_json_sha256(
            llm_preflight_fields
        ),
        "case_promotion_doctor_preflight_evidence_template_field_count": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_FIELD_COUNT
        ),
        "case_promotion_doctor_preflight_evidence_template_sha256": (
            DOCTOR_PREFLIGHT_EVIDENCE_TEMPLATE_SHA256
        ),
        "case_promotion_command_plan_summary": plan.case_promotion_command_plan_summary,
        "standard_release_flow": plan.standard_release_flow,
        "standard_release_flow_status": plan.standard_release_flow["status"],
        "standard_release_flow_primary_next_action": plan.standard_release_flow[
            "primary_next_action"
        ],
        "standard_release_flow_command_count": plan.standard_release_flow["command_count"],
        "standard_release_flow_commands_sha256": plan.standard_release_flow[
            "commands_sha256"
        ],
        "standard_release_flow_step_count": len(standard_release_flow_steps),
        "standard_release_flow_step_names": standard_release_flow_step_names,
        "standard_release_flow_step_names_sha256": _stable_json_sha256(
            standard_release_flow_step_names
        ),
        "standard_release_flow_steps_sha256": _stable_json_sha256(
            standard_release_flow_steps
        ),
        "standard_release_flow_first_step_name": "strict_release_readiness",
        "standard_release_flow_last_step_name": "remote_publication_audit",
        "standard_release_flow_step_boundary_sha256": _stable_json_sha256(
            standard_release_flow_step_boundary
        ),
        "standard_release_flow_step_status_counts": standard_release_flow_step_status_counts,
        "standard_release_flow_step_status_counts_sha256": _stable_json_sha256(
            standard_release_flow_step_status_counts
        ),
        **expected_standard_release_flow_primary_step_handoff_aliases,
        "standard_release_flow_has_website_deploy": True,
        "standard_release_flow_website_deploy_command": WEBSITE_DEPLOY_COMMAND,
        "standard_release_flow_website_deploy_command_sha256": _stable_json_sha256(
            WEBSITE_DEPLOY_COMMAND
        ),
        "standard_release_flow_has_website_inspect": True,
        "standard_release_flow_website_inspect_command": WEBSITE_INSPECT_COMMAND,
        "standard_release_flow_website_inspect_command_sha256": _stable_json_sha256(
            WEBSITE_INSPECT_COMMAND
        ),
        "standard_release_flow_has_distribution_audit": True,
        "standard_release_flow_distribution_audit_command": DISTRIBUTION_AUDIT_COMMAND,
        "standard_release_flow_distribution_audit_command_sha256": _stable_json_sha256(
            DISTRIBUTION_AUDIT_COMMAND
        ),
        "standard_release_flow_sha256": _stable_json_sha256(plan.standard_release_flow),
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
        "publication_blocker_count": len(expected_publication_blockers),
        "publication_blockers_sha256": _stable_json_sha256(expected_publication_blockers),
        "publication_primary_blocker": expected_publication_blockers[0],
        "publication_blockers": expected_publication_blockers,
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
                "promotion_command_plan, llm_live_preflight_required, "
                "llm_live_preflight_command, llm_live_preflight_blocker_note, and "
                "llm_live_preflight_evidence_fields / doctor_preflight_evidence_fields "
                "for each case."
            ),
            "Review each body file for scope, tasks, validation evidence, and non-goals.",
            (
                "If candidate_issue_gate.requires_maintainer_review is true, set "
                "CLIANY_CREATE_ISSUES_ACK_REVIEW=1 only after completing that review."
            ),
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
    assert planner_handoff == plan_next_iteration._handoff_payload(plan)
    assert artifact_manifest["files"]["planner_handoff"] == "planner-handoff.json"
    assert "planner-handoff.json" in artifact_manifest["review_order"]
    assert publication_handoff == expected_publication_handoff
    assert release_draft_handoff == expected_release_draft_handoff
    assert "gh issue create" in script
    assert 'REPO_ROOT="$(git rev-parse --show-toplevel)"' in script
    assert 'cd "$REPO_ROOT"' in script
    assert "CLIANY_CREATE_ISSUES_DRY_RUN" in script
    assert "Dry run: candidate issue gate preflight and gh issue create are not executed." in script
    assert "cat <<'CLIANY_ISSUE_COMMANDS'" in script
    assert "CLIANY_ISSUE_COMMANDS" in script
    assert 'PYTHON_BIN="${PYTHON_BIN:-python3}"' in script
    assert 'PREFLIGHT_JSON="/tmp/cliany-issue-gate-check.json"' in script
    assert (
        'if ! "$PYTHON_BIN" scripts/plan_next_iteration.py --target-version 0.16.2 --json >"$PREFLIGHT_JSON"; then'
    ) in script
    assert 'if ! "$PYTHON_BIN" - "$PREFLIGHT_JSON" <<\'PY\'' in script
    assert (
        'if ! python scripts/plan_next_iteration.py --target-version 0.16.2 --json >"$PREFLIGHT_JSON"; then'
    ) not in script
    assert 'if ! python - "$PREFLIGHT_JSON" <<\'PY\'' not in script
    assert "Candidate issue gate preflight failed; review $PREFLIGHT_JSON" in script
    assert "candidate_issue_gate" in script
    assert "can_create_issues" in script
    assert "requires_maintainer_review" in script
    assert "Candidate issue gate does not allow creating issues." in script
    assert "Candidate issue gate requires maintainer review before creating issues." in script
    assert "CLIANY_CREATE_ISSUES_ACK_REVIEW" in script
    assert 'os.environ.get("CLIANY_CREATE_ISSUES_ACK_REVIEW") != "1"' in script
    assert "Set CLIANY_CREATE_ISSUES_ACK_REVIEW=1 after maintainer review" in script
    assert 'cat "$PREFLIGHT_JSON" >&2 || true' in script
    assert "  exit 1" in script
    assert "--body-file" in script
    assert "pypi-project-search.md" in script
    if sys.platform != "win32":
        assert oct((issues_dir / "create-issues.sh").stat().st_mode & 0o777) == "0o755"
    assert "# cliany-site Candidate Issue Artifacts" in readme
    assert "Generated for target version `0.16.2`." in readme
    assert "`issue-metadata.json`: structured issue title, labels, reproduction context" in readme
    assert "`planner-handoff.json`: compact release handoff" in readme
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
    assert "## Planner Handoff" in readme
    assert "- handoff_sha256:" in readme
    assert "## Candidate Summary" in readme
    assert (
        "| Case | Issue Body | Target URL | Candidate Commands | Offline Validation Commands | "
        "Promotion Command Plan Summary | Priority Rank | Priority Reason | "
        "Primary Evidence Task | Primary Evidence Status | Primary Acceptance Criteria | "
        "Evidence Bundle Primary Next Task | "
        "Evidence Bundle Primary Runbook | LLM Preflight Evidence Fields | "
        "Doctor Preflight Evidence Fields | "
        "Candidate Package Validation | Issue Template | Issue Template JSON | "
        "Evidence Bundle | Evidence Bundle JSON |"
    ) in readme
    assert (
        "| `pypi-project-search` | `pypi-project-search.md` | "
        "https://pypi.org/search/?q=cliany-site | 2 | 2 | "
        "`promotion_command_plan_summary: command_count=4, missing_command_count=0, all_declared=true` | "
        "`1` | rank 1: complete 0/3, pending 3, blocked 0, missing commands 0 | "
        "`adapter_package` | `pending` | "
        "Attach the generated <domain>-<version>.cliany-adapter.tar.gz "
        "package path or GitHub Release asset name. | `adapter_package` | "
        "`llm_live_preflight -> adapter_package -> acceptance` | "
        "`summary.ready_for_explore`, `summary.llm_live_preflight`, "
        "`summary.capabilities.generate_adapters.ready`, "
        "`checks[llm_live].status`, `checks[llm_live].details.error_code`, "
        "`checks[llm_live].details.retryable`, `checks[llm_live].details.status_code`, "
        "`checks[llm_live].details.phase`, `checks[llm_live].details.message` | "
        "`summary.ready_for_explore`, `summary.capabilities.run_browser_workflows.ready`, "
        "`summary.capabilities.generate_adapters.ready`, `checks[cdp].status`, "
        "`checks[cdp].action`, `checks[llm_live].status`, "
        "`checks[llm_live].details.error_code`, `checks[llm_live].details.retryable`, "
        "`checks[llm_live].details.phase`, `checks[llm_live].details.message` | "
        "`python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict` | "
        "`cliany-site cases --case-id pypi-project-search --issue-template` | "
        "`cliany-site cases --case-id pypi-project-search --issue-template --json` | "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle` | "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle --json` |"
    ) in readme
    assert "## Candidate Promotion Evidence Summary" in readme
    assert "| pending_count | `6` |" in readme
    assert "| primary_next_action | `Generate pypi.org-<version>.cliany-adapter.tar.gz.` |" in readme
    assert "| primary_next_task_acceptance_criteria | `-" in readme
    assert (
        "| `pypi-project-search` | `adapter_package` | `pending` | - | "
        "Generate pypi.org-<version>.cliany-adapter.tar.gz. | - |"
    ) in readme
    assert "## Issue Body Inventory" in readme
    assert "| Case | Issue Body | Bytes | SHA-256 | Promotion Command Plan Summary |" in readme
    assert (
        f"| `pypi-project-search` | `pypi-project-search.md` | "
        f"{issue_body_inventory[0]['byte_count']} | `{issue_body_inventory[0]['sha256']}` | "
        "`promotion_command_plan_summary: command_count=4, missing_command_count=0, all_declared=true` |"
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
    assert (
        "case_promotion_evidence_summary_last_key: "
        "`llm_live_preflight_evidence_fields_sha256`"
    ) in readme
    assert "primary_task_detail" in readme
    assert "llm_live_preflight_evidence_fields_sha256" in readme
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
        "case_promotion_evidence_primary_expected_adapter_package: "
        "`pypi.org-<version>.cliany-adapter.tar.gz`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_acceptance_criteria: "
        "`Attach the generated <domain>-<version>.cliany-adapter.tar.gz package path "
        "or GitHub Release asset name.`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_acceptance_criteria_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_acceptance_criteria_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_primary_priority_rank: `1`" in readme
    assert (
        "case_promotion_evidence_primary_priority_reason: "
        "`rank 1: complete 0/3, pending 3, blocked 0, missing commands 0`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_issue_template_command: "
        "`cliany-site cases --case-id pypi-project-search --issue-template`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_issue_template_json_command: "
        "`cliany-site cases --case-id pypi-project-search --issue-template --json`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_evidence_bundle_command: "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_evidence_bundle_json_command: "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle --json`"
    ) in readme
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
    assert "case_promotion_evidence_primary_runbook_step_count: `3`" in readme
    assert (
        "case_promotion_evidence_primary_runbook_steps: "
        "`[\"llm_live_preflight\", \"adapter_package\", \"acceptance\"]`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_runbook_steps_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_runbook_steps_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_primary_runbook_first_step: `llm_live_preflight`" in readme
    assert (
        "case_promotion_evidence_primary_runbook_first_command: "
        "`cliany-site doctor --llm-live --json`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_runbook_first_command_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_runbook_first_command_sha256']}`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_runbook_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_runbook_sha256']}`"
    ) in readme
    assert "case_promotion_evidence_primary_llm_live_preflight_required: `true`" in readme
    assert (
        "case_promotion_evidence_primary_llm_live_preflight_command: "
        "`cliany-site doctor --llm-live --json`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_llm_live_preflight_command_sha256: "
        f"`{artifact_bundle_summary['case_promotion_evidence_primary_llm_live_preflight_command_sha256']}`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_llm_live_preflight_blocker_note: "
        f"`{plan_next_iteration.LLM_LIVE_PREFLIGHT_BLOCKER_NOTE}`"
    ) in readme
    assert (
        "case_promotion_evidence_primary_llm_live_preflight_blocker_comment: "
        f"{plan_next_iteration._summary_inline_code(LLM_LIVE_PREFLIGHT_BLOCKER_COMMENT)}"
    ) in readme
    assert (
        "case_promotion_evidence_primary_doctor_preflight_blocker_comment: "
        f"{plan_next_iteration._summary_inline_code(DOCTOR_PREFLIGHT_BLOCKER_COMMENT)}"
    ) in readme
    assert "case_promotion_llm_live_preflight_evidence_field_count: `9`" in readme
    assert (
        "case_promotion_llm_live_preflight_evidence_fields: "
        "`[\"summary.ready_for_explore\", \"summary.llm_live_preflight\""
    ) in readme
    assert (
        "case_promotion_llm_live_preflight_evidence_fields_sha256: "
        f"`{artifact_bundle_summary['case_promotion_llm_live_preflight_evidence_fields_sha256']}`"
    ) in readme
    assert (
        "case_promotion_command_plan_summary_sha256: "
        f"`{artifact_bundle_summary['case_promotion_command_plan_summary_sha256']}`"
    ) in readme
    assert "case_promotion_command_plan_candidate_count: `2`" in readme
    assert "case_promotion_command_plan_command_count: `8`" in readme
    assert "case_promotion_command_plan_missing_command_count: `1`" in readme
    assert "case_promotion_command_plan_all_declared: `false`" in readme
    assert "standard_release_flow_status: `blocked`" in readme
    assert "standard_release_flow_target_tag: `v0.16.2`" in readme
    assert (
        "standard_release_flow_primary_next_action: "
        "`Commit, stash, or discard local worktree changes before publishing release refs.`"
    ) in readme
    assert (
        "standard_release_flow_command_count: "
        f"`{plan.standard_release_flow['command_count']}`"
    ) in readme
    assert (
        "standard_release_flow_commands_sha256: "
        f"`{plan.standard_release_flow['commands_sha256']}`"
    ) in readme
    assert (
        f"standard_release_flow_step_count: `{len(plan.standard_release_flow['steps'])}`"
        in readme
    )
    assert (
        "standard_release_flow_step_names: "
        f"`{json.dumps(standard_release_flow_step_names, ensure_ascii=False)}`"
    ) in readme
    assert (
        "standard_release_flow_step_names_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_step_names)}`"
    ) in readme
    assert (
        "standard_release_flow_steps_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_steps)}`"
    ) in readme
    assert "standard_release_flow_first_step_name: `strict_release_readiness`" in readme
    assert "standard_release_flow_last_step_name: `remote_publication_audit`" in readme
    assert (
        "standard_release_flow_step_boundary_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_step_boundary)}`"
    ) in readme
    assert (
        "standard_release_flow_step_status_counts: "
        f"`{json.dumps(standard_release_flow_step_status_counts, ensure_ascii=False)}`"
    ) in readme
    assert (
        "standard_release_flow_step_status_counts_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_step_status_counts)}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_name: "
        f"`{_standard_release_flow_primary_step_name_with_status_prefix(standard_release_flow_steps, 'blocked')}`"
    ) in readme
    primary_blocked_step = next(
        step
        for step in standard_release_flow_steps
        if str(step.get("status")).startswith("blocked")
    )
    assert (
        "standard_release_flow_primary_blocked_step_command: "
        f"`{primary_blocked_step['command']}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_status: "
        f"`{primary_blocked_step['status']}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_status_sha256: "
        f"`{_stable_json_sha256(primary_blocked_step['status'])}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_command_sha256: "
        f"`{_stable_json_sha256(primary_blocked_step['command'])}`"
    ) in readme
    assert "standard_release_flow_primary_blocked_step_action: `(none)`" in readme
    assert (
        "standard_release_flow_primary_blocked_step_action_sha256: `(none)`"
        in readme
    )
    assert "standard_release_flow_primary_pending_step_name: `release_notes`" in readme
    primary_pending_step = next(
        step
        for step in standard_release_flow_steps
        if str(step.get("status")).startswith("pending")
    )
    assert "standard_release_flow_primary_pending_step_command: `(none)`" in readme
    assert (
        "standard_release_flow_primary_pending_step_command_sha256: `(none)`"
        in readme
    )
    assert (
        "standard_release_flow_primary_pending_step_action: "
        f"{plan_next_iteration._summary_inline_code(primary_pending_step['action'])}"
    ) in readme
    assert (
        "standard_release_flow_primary_pending_step_status: "
        f"`{primary_pending_step['status']}`"
    ) in readme
    assert (
        "standard_release_flow_primary_pending_step_status_sha256: "
        f"`{_stable_json_sha256(primary_pending_step['status'])}`"
    ) in readme
    assert (
        "standard_release_flow_primary_pending_step_action_sha256: "
        f"`{_stable_json_sha256(primary_pending_step['action'])}`"
    ) in readme
    assert "standard_release_flow_has_website_deploy: `true`" in readme
    assert (
        f"standard_release_flow_website_deploy_command: `{WEBSITE_DEPLOY_COMMAND}`"
        in readme
    )
    assert (
        "standard_release_flow_website_deploy_command_sha256: "
        f"`{_stable_json_sha256(WEBSITE_DEPLOY_COMMAND)}`"
    ) in readme
    assert "standard_release_flow_has_website_inspect: `true`" in readme
    assert (
        f"standard_release_flow_website_inspect_command: `{WEBSITE_INSPECT_COMMAND}`"
        in readme
    )
    assert (
        "standard_release_flow_website_inspect_command_sha256: "
        f"`{_stable_json_sha256(WEBSITE_INSPECT_COMMAND)}`"
    ) in readme
    assert "standard_release_flow_has_distribution_audit: `true`" in readme
    assert (
        "standard_release_flow_distribution_audit_command: "
        f"`{DISTRIBUTION_AUDIT_COMMAND}`"
    ) in readme
    assert (
        "standard_release_flow_distribution_audit_command_sha256: "
        f"`{_stable_json_sha256(DISTRIBUTION_AUDIT_COMMAND)}`"
    ) in readme
    assert (
        "standard_release_flow_sha256: "
        f"`{_stable_json_sha256(plan.standard_release_flow)}`"
    ) in readme
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
    assert "review_item_count: `8`" in readme
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
    assert "artifact_files_key_count: `7`" in readme
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
    assert (
        "publication_target_tag: "
        f"`{artifact_bundle_summary['publication_target_tag']}`"
    ) in readme
    assert (
        "publication_target_tag_status: "
        f"`{artifact_bundle_summary['publication_target_tag_status']}`"
    ) in readme
    assert (
        "publication_target_tag_primary_command: "
        f"`{artifact_bundle_summary['publication_target_tag_primary_command']}`"
    ) in readme
    assert (
        "publication_target_tag_command_count: "
        f"`{artifact_bundle_summary['publication_target_tag_command_count']}`"
    ) in readme
    assert (
        "publication_target_tag_commands_sha256: "
        f"`{artifact_bundle_summary['publication_target_tag_commands_sha256']}`"
    ) in readme
    assert (
        "publication_target_tag_required_action_sha256: "
        f"`{artifact_bundle_summary['publication_target_tag_required_action_sha256']}`"
    ) in readme
    assert (
        "publication_target_tag_release_gate_status: "
        f"`{artifact_bundle_summary['publication_target_tag_release_gate_status']}`"
    ) in readme
    assert (
        "publication_target_tag_release_gate_blocker_count: "
        f"`{artifact_bundle_summary['publication_target_tag_release_gate_blocker_count']}`"
    ) in readme
    assert (
        "publication_target_tag_release_gate_primary_blocker: "
        f"`{artifact_bundle_summary['publication_target_tag_release_gate_primary_blocker']}`"
    ) in readme
    assert (
        "publication_target_tag_release_gate_required_action_sha256: "
        f"`{artifact_bundle_summary['publication_target_tag_release_gate_required_action_sha256']}`"
    ) in readme
    assert (
        "publication_target_tag_release_gate_blockers_sha256: "
        f"`{artifact_bundle_summary['publication_target_tag_release_gate_blockers_sha256']}`"
    ) in readme
    assert (
        "publication_blocker_count: "
        f"`{artifact_bundle_summary['publication_blocker_count']}`"
    ) in readme
    assert (
        "publication_blockers_sha256: "
        f"`{artifact_bundle_summary['publication_blockers_sha256']}`"
    ) in readme
    assert (
        "publication_primary_blocker: "
        f"{plan_next_iteration._summary_inline_code(artifact_bundle_summary['publication_primary_blocker'])}"
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
    assert f"publication_handoff_key_count: `{len(expected_publication_handoff)}`" in readme
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
    assert "review_checklist_count: `8`" in readme
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
    assert "create_issues_safety_contract_key_count: `7`" in readme
    assert (
        "create_issues_safety_contract_sha256: "
        f"`{artifact_bundle_summary['create_issues_safety_contract_sha256']}`"
    ) in readme
    assert "create_issues_safety_contract_first_key: `dry_run_supported`" in readme
    assert (
        "create_issues_safety_contract_last_key: "
        "`maintainer_review_ack_required_when`"
    ) in readme
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
    assert (
        "candidate_issue_gate_evidence_key_count: "
        f"`{len(_blocked_candidate_issue_gate()['evidence'])}`"
    ) in readme
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
    assert "gate_evidence_target_tag: `v0.16.2`" in readme
    assert "gate_evidence_target_tag_status: `blocked_by_worktree`" in readme
    assert "gate_evidence_target_tag_primary_command: `git tag v0.16.2`" in readme
    assert (
        f"gate_evidence_target_tag_commands_sha256: "
        f"`{_stable_json_sha256(['git tag v0.16.2', 'git push origin v0.16.2'])}`"
    ) in readme
    assert "gate_evidence_target_tag_release_gate_status: `blocked_by_readiness`" in readme
    assert "gate_evidence_target_tag_release_gate_blocker_count: `1`" in readme
    assert (
        "gate_evidence_target_tag_release_gate_primary_blocker: "
        "`release draft validation failed`"
    ) in readme
    assert (
        f"gate_evidence_target_tag_release_gate_blockers_sha256: "
        f"`{_stable_json_sha256(['release draft validation failed'])}`"
    ) in readme
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
    assert "standard_release_flow_status: `blocked`" in readme
    assert "standard_release_flow_target_tag: `v0.16.2`" in readme
    assert (
        "standard_release_flow_command_count: "
        f"`{plan.standard_release_flow['command_count']}`"
    ) in readme
    assert (
        f"standard_release_flow_step_count: `{len(plan.standard_release_flow['steps'])}`"
        in readme
    )
    assert (
        "standard_release_flow_step_names: "
        f"`{json.dumps(standard_release_flow_step_names, ensure_ascii=False)}`"
    ) in readme
    assert (
        "standard_release_flow_step_names_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_step_names)}`"
    ) in readme
    assert (
        "standard_release_flow_steps_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_steps)}`"
    ) in readme
    assert "standard_release_flow_first_step_name: `strict_release_readiness`" in readme
    assert "standard_release_flow_last_step_name: `remote_publication_audit`" in readme
    assert (
        "standard_release_flow_step_boundary_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_step_boundary)}`"
    ) in readme
    assert (
        "standard_release_flow_step_status_counts: "
        f"`{json.dumps(standard_release_flow_step_status_counts, ensure_ascii=False)}`"
    ) in readme
    assert (
        "standard_release_flow_step_status_counts_sha256: "
        f"`{_stable_json_sha256(standard_release_flow_step_status_counts)}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_name: "
        f"`{_standard_release_flow_primary_step_name_with_status_prefix(standard_release_flow_steps, 'blocked')}`"
    ) in readme
    primary_blocked_step = next(
        step
        for step in standard_release_flow_steps
        if str(step.get("status")).startswith("blocked")
    )
    assert (
        "standard_release_flow_primary_blocked_step_command: "
        f"`{primary_blocked_step['command']}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_status: "
        f"`{primary_blocked_step['status']}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_status_sha256: "
        f"`{_stable_json_sha256(primary_blocked_step['status'])}`"
    ) in readme
    assert (
        "standard_release_flow_primary_blocked_step_command_sha256: "
        f"`{_stable_json_sha256(primary_blocked_step['command'])}`"
    ) in readme
    assert "standard_release_flow_primary_blocked_step_action: `(none)`" in readme
    assert (
        "standard_release_flow_primary_blocked_step_action_sha256: `(none)`"
        in readme
    )
    assert "standard_release_flow_primary_pending_step_name: `release_notes`" in readme
    primary_pending_step = next(
        step
        for step in standard_release_flow_steps
        if str(step.get("status")).startswith("pending")
    )
    assert "standard_release_flow_primary_pending_step_command: `(none)`" in readme
    assert (
        "standard_release_flow_primary_pending_step_command_sha256: `(none)`"
        in readme
    )
    assert (
        "standard_release_flow_primary_pending_step_action: "
        f"{plan_next_iteration._summary_inline_code(primary_pending_step['action'])}"
    ) in readme
    assert (
        "standard_release_flow_primary_pending_step_status: "
        f"`{primary_pending_step['status']}`"
    ) in readme
    assert (
        "standard_release_flow_primary_pending_step_status_sha256: "
        f"`{_stable_json_sha256(primary_pending_step['status'])}`"
    ) in readme
    assert (
        "standard_release_flow_primary_pending_step_action_sha256: "
        f"`{_stable_json_sha256(primary_pending_step['action'])}`"
    ) in readme
    assert "standard_release_flow_has_website_deploy: `true`" in readme
    assert (
        f"standard_release_flow_website_deploy_command: `{WEBSITE_DEPLOY_COMMAND}`"
        in readme
    )
    assert "standard_release_flow_has_website_inspect: `true`" in readme
    assert (
        f"standard_release_flow_website_inspect_command: `{WEBSITE_INSPECT_COMMAND}`"
        in readme
    )
    assert "standard_release_flow_has_distribution_audit: `true`" in readme
    assert (
        "standard_release_flow_distribution_audit_command: "
        f"`{DISTRIBUTION_AUDIT_COMMAND}`"
    ) in readme
    assert (
        "standard_release_flow_distribution_audit_command_sha256: "
        f"`{_stable_json_sha256(DISTRIBUTION_AUDIT_COMMAND)}`"
    ) in readme
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
    assert "CLIANY_CREATE_ISSUES_ACK_REVIEW=1 only after completing that review" in readme
    assert "expected target URL, candidate commands" in readme
    assert (
        "offline validation commands, candidate_package_validation_command, "
        "promotion_command_plan, llm_live_preflight_required, "
        "llm_live_preflight_command, llm_live_preflight_blocker_note, and "
        "llm_live_preflight_evidence_fields / doctor_preflight_evidence_fields for each case"
        in readme
    )
    assert "candidate issue gate preflight" in readme
    assert "python scripts/plan_next_iteration.py --target-version 0.16.2 --json" in readme
    assert "/tmp/cliany-issue-gate-check.json" in readme
    assert "prints the preflight JSON before exiting" in readme
    assert "### Create Issues Safety" in readme
    assert "dry_run_supported: `true`" in readme
    assert "dry_run_env: `CLIANY_CREATE_ISSUES_DRY_RUN=1`" in readme
    assert "dry_run_command: `CLIANY_CREATE_ISSUES_DRY_RUN=1 create-issues.sh`" in readme
    assert "preflight_required: `true`" in readme
    assert (
        "preflight_command: `python scripts/plan_next_iteration.py "
        "--target-version 0.16.2 --json`"
    ) in readme
    assert "preflight_json: `/tmp/cliany-issue-gate-check.json`" in readme
    assert "maintainer_review_ack_env: `CLIANY_CREATE_ISSUES_ACK_REVIEW=1`" in readme
    assert (
        "maintainer_review_ack_required_when: "
        "`candidate_issue_gate.requires_maintainer_review=true`"
    ) in readme
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
    if sys.platform == "win32":
        pytest.skip("stdout-heavy planner JSON is covered by Linux CI")

    exit_code = plan_next_iteration.main(["--json", "--target-version", "0.16.2"])

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["target_version"] == "0.16.2"
    assert "recommended_theme" in payload
    assert "case_promotion_evidence_summary" in payload
    assert "next_actions" in payload
