import json
from pathlib import Path

from click.testing import CliRunner

from cliany_site.cli import cli
from cliany_site.commands.cases import _print_human_cases

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


def test_cases_command_returns_catalog_summary(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "cases"], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "cases"
    data = payload["data"]
    assert data["summary"]["catalog_total"] >= 8
    assert data["summary"]["active_count"] >= 4
    assert data["summary"]["candidate_count"] >= 3
    assert data["summary"]["status_counts"]["active"] >= 4
    assert data["promotion_evidence_summary"]["candidate_count"] >= 3
    assert data["promotion_evidence_summary"]["pending_count"] >= 9
    assert data["promotion_evidence_summary"]["primary_task_detail"]["case_id"] == "pypi-project-search"
    assert data["promotion_evidence_summary"]["primary_task_detail"]["task"] == "adapter_package"
    assert data["promotion_evidence_summary"]["primary_task_detail"]["status"] == "pending"
    assert data["promotion_evidence_summary"]["primary_task_detail"]["evidence"] == ""
    assert data["promotion_evidence_summary"]["primary_task_detail"][
        "acceptance_criteria"
    ].startswith("Attach the generated")
    assert (
        data["promotion_evidence_summary"]["primary_task_detail"][
            "llm_live_preflight_required"
        ]
        is True
    )
    assert (
        data["promotion_evidence_summary"]["primary_task_detail"][
            "llm_live_preflight_command"
        ]
        == "cliany-site doctor --llm-live --json"
    )
    assert data["promotion_evidence_summary"][
        "primary_next_task_acceptance_criteria"
    ].startswith("Attach the generated")
    assert (
        data["promotion_evidence_summary"]["primary_next_task_runbook_first_step"]
        == "llm_live_preflight"
    )
    assert (
        data["promotion_evidence_summary"]["primary_next_task_runbook_first_command"]
        == "cliany-site doctor --llm-live --json"
    )
    assert (
        data["promotion_evidence_summary"]["primary_next_task_runbook_first_command_sha256"]
        == "0ca644df288169289dd4dbc17aeacdc58b9898f05c0d4c5d304c17e33bdbcb96"
    )
    assert (
        data["promotion_evidence_summary"]["primary_next_task"]
        == data["promotion_evidence_summary"]["primary_task_detail"]
    )
    assert any(case["id"] == "suitecrm-accounts" for case in data["cases"])
    assert any("offline_commands" in case for case in data["cases"])


def test_cases_command_filters_candidates_with_detail(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "cases", "--status", "candidate", "--detail"], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    data = payload["data"]
    assert data["status_filter"] == "candidate"
    assert data["summary"]["total"] == data["summary"]["candidate_count"]
    assert data["promotion_evidence_summary"]["primary_case_id"] == "pypi-project-search"
    assert data["promotion_evidence_summary"]["primary_task"] == "adapter_package"
    assert data["promotion_evidence_summary"]["primary_task_detail"] == {
        "case_id": "pypi-project-search",
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": data["promotion_evidence_summary"]["primary_next_action"],
        "acceptance_criteria": data["promotion_evidence_summary"][
            "primary_next_task_acceptance_criteria"
        ],
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "llm_live_preflight_required": True,
        "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
        "llm_live_preflight_blocker_note": (
            "Run the live LLM preflight before explore. If generate_adapters.ready=false "
            "or llm_live reports warning/error such as E_LLM_UNAVAILABLE "
            "(including provider connection failure), stop candidate promotion, attach "
            "the doctor JSON/error summary, and leave adapter_package pending or blocked."
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
        "doctor_preflight_evidence_fields": DOCTOR_PREFLIGHT_EVIDENCE_FIELDS,
    }
    assert (
        data["promotion_evidence_summary"]["primary_next_task"]
        == data["promotion_evidence_summary"]["primary_task_detail"]
    )
    assert "Generate pypi.org" in data["promotion_evidence_summary"]["primary_next_action"]
    assert {case["status"] for case in data["cases"]} == {"candidate"}
    assert all("promotion" in case for case in data["cases"])
    assert all("promotion_evidence" in case for case in data["cases"])
    assert all("promotion_command_plan" in case for case in data["cases"])
    assert data["cases"][0]["promotion_command_plan"][0] == {
        "task": "llm_live_preflight",
        "command": "cliany-site doctor --llm-live --json",
        "source": "doctor.llm_live",
        "missing": False,
    }
    assert data["cases"][0]["promotion_command_plan"][1] == {
        "task": "adapter_package",
        "command": (
            'cliany-site explore "https://pypi.org" '
            '"search Python packages for cliany-site and list project names" --json'
        ),
        "source": "commands.explore",
        "missing": False,
    }


def test_cases_command_filters_exact_case_with_implicit_detail(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--case-id", "pypi-project-search"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    data = payload["data"]
    assert data["case_id"] == "pypi-project-search"
    assert data["summary"]["total"] == 1
    assert data["promotion_evidence_summary"]["primary_case_id"] == "pypi-project-search"
    case = data["cases"][0]
    assert case["id"] == "pypi-project-search"
    assert case["status"] == "candidate"
    assert "promotion" in case
    assert "promotion_evidence" in case
    assert case["commands"][0].startswith("cliany-site explore")
    assert "python scripts/validate_cases.py --strict" in case["offline_commands"]


def test_cases_command_human_output_shows_first_commands(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["cases", "--status", "active"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "cliany-site cases" in result.output
    assert "suitecrm-accounts" in result.output
    assert "cliany-site market install" in result.output


def test_cases_command_human_candidate_next_step_shows_primary_detail(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["cases", "--status", "candidate"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Candidate 下一步" in result.output
    assert "pypi-project-search/adapter_package (pending)" in result.output
    assert "evidence: Not attached yet." in result.output
    assert "acceptance: Attach the generated" in result.output
    assert "package path or release asset name" in result.output
    assert "preflight_required: true" in result.output
    assert "preflight_blocker: Run the live LLM preflight before explore." in result.output


def test_cases_human_output_uses_primary_next_task(capsys):
    _print_human_cases(
        {
            "cases": [
                {
                    "id": "candidate-case",
                    "status": "candidate",
                    "category": "demo",
                    "adapter_domain": "example.com",
                    "commands": ["cliany-site example.com list --json"],
                }
            ],
            "summary": {
                "total": 1,
                "active_count": 0,
                "candidate_count": 1,
                "known_gap_count": 0,
            },
            "source_path": "cases/manifest.json",
            "promotion_evidence_summary": {
                "primary_task_detail": {
                    "case_id": "legacy-case",
                    "task": "legacy_task",
                    "status": "blocked",
                    "evidence": "legacy evidence",
                    "next_action": "Legacy next action.",
                },
                "primary_next_task": {
                    "case_id": "candidate-case",
                    "task": "adapter_package",
                    "status": "pending",
                    "evidence": "",
                    "next_action": "Generate the adapter package.",
                },
                "primary_case_id": "legacy-case",
                "primary_task": "legacy_task",
                "primary_next_action": "Legacy next action.",
            },
        },
        detail=False,
    )

    text = capsys.readouterr().out
    assert "candidate-case/adapter_package (pending)" in text
    assert "Generate the adapter package." in text
    assert "legacy-case/legacy_task" not in text


def test_cases_command_human_case_detail_shows_all_commands(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["cases", "--case-id", "pypi-project-search"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "案例详情" in result.output
    assert "pypi-project-search" in result.output
    assert "https://pypi.org/search/?q=cliany-site" in result.output
    assert "Validation" in result.output
    assert "Promotion Tasks" in result.output
    assert "adapter_package: pending" in result.output
    assert "Generate pypi.org" in result.output
    assert "cliany-site explore" in result.output
    assert "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json" in result.output
    assert "python scripts/validate_cases.py --strict" in result.output


def test_cases_command_issue_template_json(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--case-id", "pypi-project-search", "--issue-template"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    template = payload["data"]["issue_template"]
    primary_task = payload["data"]["issue_template_primary_task"]
    assert primary_task == {
        "task": "adapter_package",
        "status": "pending",
        "evidence": "",
        "next_action": (
            "Generate pypi.org-<version>.cliany-adapter.tar.gz with cliany-site explore "
            "and market publish, then attach the package path or release asset name."
        ),
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
    }
    assert "## Scope: promote candidate case `pypi-project-search`" in template
    assert "## Primary Evidence Task" in template
    assert "- Task: `adapter_package`" in template
    assert "- Status: `pending`" in template
    assert "- Expected adapter package: `pypi.org-<version>.cliany-adapter.tar.gz`" in template
    assert "## Reproduction Context" in template
    assert "## Promotion Command Plan" in template
    assert "## LLM Preflight Gate" in template
    assert "- Command: `cliany-site doctor --llm-live --json`" in template
    assert "generate_adapters.ready=false" in template
    assert "llm_live reports warning/error" in template
    assert "E_LLM_UNAVAILABLE" in template
    assert "provider connection failure" in template
    assert "leave adapter_package pending or blocked" in template
    assert "## LLM Preflight Evidence Fields" in template
    assert "`summary.ready_for_explore`" in template
    assert "`summary.llm_live_preflight`" in template
    assert "`summary.capabilities.generate_adapters.ready`" in template
    assert "`checks[llm_live].status`" in template
    assert "`checks[llm_live].details.error_code`" in template
    assert "`checks[llm_live].details.retryable`" in template
    assert "`checks[llm_live].details.status_code`" in template
    assert "`checks[llm_live].details.phase`" in template
    assert "`checks[llm_live].details.message`" in template
    assert "## Acceptance Criteria" in template
    assert "`adapter_package`: Attach the generated <domain>-<version>.cliany-adapter.tar.gz" in template
    assert "`metadata_validation`: Paste `python scripts/validate_cases.py" in template
    assert "`online_smoke`: Paste the read-only adapter command JSON envelope summary" in template
    assert (
        '`adapter_package`: `cliany-site explore "https://pypi.org" '
        '"search Python packages for cliany-site and list project names" --json`'
        in template
    )
    assert (
        "`metadata_validation`: `python scripts/validate_cases.py "
        "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict`"
        in template
    )
    assert (
        "`online_smoke`: `cliany-site pypi.org search-projects --query cliany-site "
        "--limit 5 --json`"
        in template
    )
    assert "`adapter_package`" in template
    assert "Acceptance criteria: Attach the generated <domain>-<version>.cliany-adapter.tar.gz" in template
    assert "Generate pypi.org" in template
    assert "## Evidence Bundle" in template
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle" in template
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in template
    assert "Attach or paste the JSON output in the issue once evidence changes." in template
    assert "Candidate package validation command" in template
    assert "Expected adapter package: `pypi.org-<version>.cliany-adapter.tar.gz`" in template
    assert (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
        in template
    )
    assert "Do not mark the case `active`" in template


def test_cases_command_issue_template_human_outputs_markdown(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cases", "--case-id", "pypi-project-search", "--issue-template"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "## Scope: promote candidate case `pypi-project-search`" in result.output
    assert "## Evidence Bundle" in result.output
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in result.output
    assert "## LLM Preflight Gate" in result.output
    assert "E_LLM_UNAVAILABLE" in result.output
    assert "provider connection failure" in result.output
    assert "Candidate package validation command" in result.output
    assert (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
        in result.output
    )
    assert "案例库" not in result.output


def test_cases_command_issue_template_checks_complete_tasks(tmp_home, monkeypatch):
    import cliany_site.commands.cases as cases_module

    case = {
        "id": "mixed-candidate",
        "title": "Mixed candidate",
        "status": "candidate",
        "target_url": "https://example.test/search",
        "adapter_domain": "example.test",
        "commands": ["cliany-site example.test search --json"],
        "validation": {"offline_commands": ["python scripts/validate_cases.py --strict"]},
        "promotion": {
            "adapter_package": "Build adapter package.",
            "metadata_validation": "Validate metadata.",
            "online_smoke": "Run online smoke.",
        },
        "promotion_evidence": {
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
    }
    source = tmp_home / "cases" / "manifest.json"
    monkeypatch.setattr(cases_module, "_load_cases_manifest", lambda: ([case], source, [source]))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cases", "--case-id", "mixed-candidate", "--issue-template"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(
        runner.invoke(
            cli,
            ["--json", "cases", "--case-id", "mixed-candidate", "--issue-template"],
            catch_exceptions=False,
        ).output
    )
    assert payload["data"]["issue_template_primary_task"] == {
        "task": "online_smoke",
        "status": "pending",
        "evidence": "",
        "next_action": "Run read-only smoke.",
        "expected_adapter_package": "example.test-<version>.cliany-adapter.tar.gz",
    }
    assert "## Primary Evidence Task" in result.output
    assert "- Task: `online_smoke`" in result.output
    assert "- Status: `pending`" in result.output
    assert "- Next action: Run read-only smoke." in result.output
    assert "- Acceptance criteria: Paste the read-only adapter command JSON envelope summary" in result.output
    assert "## Acceptance Criteria" in result.output
    assert "- [x] `adapter_package`: Build adapter package." in result.output
    assert "- [ ] `metadata_validation`: Validate metadata." in result.output
    assert "- [ ] `online_smoke`: Run online smoke." in result.output


def test_cases_command_evidence_bundle_json(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--case-id", "pypi-project-search", "--evidence-bundle"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    bundle = payload["data"]["evidence_bundle"]
    assert bundle["case_id"] == "pypi-project-search"
    assert bundle["expected_adapter_package"] == "pypi.org-<version>.cliany-adapter.tar.gz"
    assert bundle["expected_adapter_package_sha256"] == (
        "d8f01afdd80df4b44821838c4a0b555cbec833de8bc881baf85b1036bfff7bab"
    )
    assert bundle["ready_to_promote"] is False
    assert bundle["status_counts"] == {"pending": 3, "blocked": 0, "complete": 0}
    assert bundle["pending_task_count"] == 3
    assert bundle["blocked_task_count"] == 0
    assert bundle["complete_task_count"] == 0
    assert bundle["incomplete_task_count"] == 3
    assert bundle["pending_tasks"] == ["adapter_package", "metadata_validation", "online_smoke"]
    assert bundle["blocked_tasks"] == []
    assert bundle["complete_tasks"] == []
    assert bundle["incomplete_tasks"] == ["adapter_package", "metadata_validation", "online_smoke"]
    assert bundle["primary_pending_task"]["task"] == "adapter_package"
    assert bundle["primary_blocked_task"] is None
    assert bundle["primary_incomplete_task"]["task"] == "adapter_package"
    assert bundle["primary_next_task"]["task"] == "adapter_package"
    assert (
        bundle["primary_next_task"]["expected_adapter_package"]
        == "pypi.org-<version>.cliany-adapter.tar.gz"
    )
    assert bundle["primary_next_task"] == bundle["primary_pending_task"]
    assert bundle["primary_next_task_command"] == (
        'cliany-site explore "https://pypi.org" '
        '"search Python packages for cliany-site and list project names" --json'
    )
    assert bundle["primary_next_task_command_source"] == "commands.explore"
    assert bundle["primary_next_task_command_missing"] is False
    assert bundle["primary_next_task_handoff"].startswith(
        'Run `cliany-site explore "https://pypi.org"'
    )
    assert bundle["primary_next_task_runbook"] == [
        {
            "step": "llm_live_preflight",
            "command": "cliany-site doctor --llm-live --json",
            "required": True,
            "handoff": bundle["llm_live_preflight_blocker_note"],
        },
        {
            "step": "adapter_package",
            "command": (
                'cliany-site explore "https://pypi.org" '
                '"search Python packages for cliany-site and list project names" --json'
            ),
            "required": True,
            "handoff": bundle["primary_next_task_handoff"],
        },
        {
            "step": "acceptance",
            "command": "",
            "required": True,
            "handoff": (
                "Attach the generated <domain>-<version>.cliany-adapter.tar.gz package path "
                "or GitHub Release asset name."
            ),
        },
    ]
    assert bundle["primary_next_task_runbook_first_step"] == "llm_live_preflight"
    assert (
        bundle["primary_next_task_runbook_first_command"]
        == "cliany-site doctor --llm-live --json"
    )
    assert (
        bundle["primary_next_task_runbook_first_command_sha256"]
        == "0ca644df288169289dd4dbc17aeacdc58b9898f05c0d4c5d304c17e33bdbcb96"
    )
    assert bundle["primary_next_task_acceptance_criteria"] == (
        "Attach the generated <domain>-<version>.cliany-adapter.tar.gz package path "
        "or GitHub Release asset name."
    )
    assert bundle["primary_next_action"].startswith("Generate pypi.org")
    assert bundle["acceptance_criteria"] == {
        "adapter_package": (
            "Attach the generated <domain>-<version>.cliany-adapter.tar.gz package path "
            "or GitHub Release asset name."
        ),
        "metadata_validation": (
            "Paste `python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
            "--include-candidate-packages --strict` output showing the candidate package "
            "passed schema v3, manifest hash, and adapter_domain validation."
        ),
        "online_smoke": (
            "Paste the read-only adapter command JSON envelope summary with ok=true, "
            "data.quality.ok=true, and row_count>0."
        ),
    }
    assert bundle["task_handoffs"][0] == {
        "task": "adapter_package",
        "status": "pending",
        "command": (
            'cliany-site explore "https://pypi.org" '
            '"search Python packages for cliany-site and list project names" --json'
        ),
        "command_source": "commands.explore",
        "command_missing": False,
        "acceptance_criteria": bundle["tasks"][0]["acceptance_criteria"],
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "complete": False,
        "handoff": bundle["tasks"][0]["handoff"],
    }
    assert bundle["llm_live_preflight_command"] == "cliany-site doctor --llm-live --json"
    assert "generate_adapters.ready=false" in bundle["llm_live_preflight_blocker_note"]
    assert "llm_live reports warning/error" in bundle["llm_live_preflight_blocker_note"]
    assert "E_LLM_UNAVAILABLE" in bundle["llm_live_preflight_blocker_note"]
    assert "provider connection failure" in bundle["llm_live_preflight_blocker_note"]
    assert bundle["llm_live_preflight_evidence_fields"] == [
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
    assert bundle["doctor_preflight_evidence_fields"] == DOCTOR_PREFLIGHT_EVIDENCE_FIELDS
    assert bundle["promotion_command_plan_count"] == 4
    assert bundle["promotion_command_plan_missing_tasks"] == []
    assert bundle["promotion_command_plan"] == [
        {
            "task": "llm_live_preflight",
            "command": "cliany-site doctor --llm-live --json",
            "source": "doctor.llm_live",
            "missing": False,
        },
        {
            "task": "adapter_package",
            "command": (
                'cliany-site explore "https://pypi.org" '
                '"search Python packages for cliany-site and list project names" --json'
            ),
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
    assert bundle["tasks"][0]["task"] == "adapter_package"
    assert bundle["tasks"][0]["expected_adapter_package"] == (
        "pypi.org-<version>.cliany-adapter.tar.gz"
    )
    assert bundle["tasks"][0]["llm_live_preflight_required"] is True
    assert (
        bundle["tasks"][0]["llm_live_preflight_command"]
        == "cliany-site doctor --llm-live --json"
    )
    assert (
        bundle["tasks"][0]["llm_live_preflight_blocker_note"]
        == bundle["llm_live_preflight_blocker_note"]
    )
    assert (
        bundle["tasks"][0]["llm_live_preflight_evidence_fields"]
        == bundle["llm_live_preflight_evidence_fields"]
    )
    assert (
        bundle["tasks"][0]["doctor_preflight_evidence_fields"]
        == bundle["doctor_preflight_evidence_fields"]
    )
    assert (
        bundle["primary_next_task"]["doctor_preflight_evidence_fields"]
        == bundle["doctor_preflight_evidence_fields"]
    )
    assert bundle["tasks"][0]["complete"] is False
    assert bundle["tasks"][0]["command_source"] == "commands.explore"
    assert bundle["tasks"][0]["command_missing"] is False
    assert bundle["tasks"][0]["runbook"] == bundle["primary_next_task_runbook"]
    assert bundle["tasks"][0]["acceptance_criteria"].startswith("Attach the generated")
    assert bundle["tasks"][0]["handoff"].startswith(
        'Run `cliany-site explore "https://pypi.org"'
    )
    assert "python scripts/validate_cases.py --strict" in bundle["offline_commands"]
    assert bundle["candidate_package_validation_command"] == (
        "python scripts/validate_cases.py "
        "--packages-dir ~/.cliany-site/packages --include-candidate-packages --strict"
    )


def test_cases_command_evidence_bundle_splits_blocked_tasks(tmp_home, monkeypatch):
    import cliany_site.commands.cases as cases_module

    case = {
        "id": "blocked-candidate",
        "title": "Blocked candidate",
        "status": "candidate",
        "target_url": "https://example.test/search",
        "adapter_domain": "example.test",
        "docs": "docs/example.md",
        "example_output": "cases/examples/example.json",
        "commands": ["cliany-site example.test search --json"],
        "validation": {"offline_commands": ["python scripts/validate_cases.py --strict"]},
        "promotion": {
            "adapter_package": "Build adapter package.",
            "metadata_validation": "Validate metadata.",
            "online_smoke": "Run online smoke.",
        },
        "promotion_evidence": {
            "adapter_package": {
                "status": "pending",
                "evidence": None,
                "next_action": "Package the adapter.",
            },
            "metadata_validation": {
                "status": "blocked",
                "evidence": "Waiting for package artifact.",
                "next_action": "Attach package artifact first.",
            },
            "online_smoke": {
                "status": "complete",
                "evidence": "Read-only smoke passed.",
                "next_action": "",
            },
        },
    }
    source = tmp_home / "cases" / "manifest.json"
    monkeypatch.setattr(cases_module, "_load_cases_manifest", lambda: ([case], source, [source]))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--case-id", "blocked-candidate", "--evidence-bundle"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    bundle = payload["data"]["evidence_bundle"]
    assert bundle["status_counts"] == {"pending": 1, "blocked": 1, "complete": 1}
    assert bundle["pending_tasks"] == ["adapter_package"]
    assert bundle["blocked_tasks"] == ["metadata_validation"]
    assert bundle["complete_tasks"] == ["online_smoke"]
    assert bundle["incomplete_tasks"] == ["adapter_package", "metadata_validation"]
    assert bundle["primary_pending_task"]["task"] == "adapter_package"
    assert bundle["primary_blocked_task"]["task"] == "metadata_validation"
    assert bundle["primary_incomplete_task"]["task"] == "adapter_package"
    assert bundle["primary_next_task"]["task"] == "adapter_package"
    assert bundle["primary_next_task"] == bundle["primary_pending_task"]
    assert bundle["primary_next_task_command"] == ""
    assert bundle["primary_next_task_command_source"] == "commands.explore"
    assert bundle["primary_next_task_command_missing"] is True
    assert bundle["primary_next_task_handoff"] == (
        "No executable command declared for `adapter_package`; Package the adapter."
    )
    assert bundle["primary_next_task_runbook"][0] == {
        "step": "llm_live_preflight",
        "command": "cliany-site doctor --llm-live --json",
        "required": True,
        "handoff": bundle["llm_live_preflight_blocker_note"],
    }
    assert bundle["primary_next_task_runbook"][1] == {
        "step": "adapter_package",
        "command": "",
        "required": False,
        "handoff": bundle["primary_next_task_handoff"],
    }
    assert bundle["primary_next_task_acceptance_criteria"].startswith("Attach the generated")
    assert bundle["pending_task_count"] == 1
    assert bundle["blocked_task_count"] == 1
    assert bundle["complete_task_count"] == 1
    assert bundle["incomplete_task_count"] == 2
    assert bundle["ready_to_promote"] is False
    assert bundle["primary_next_action"] == "Package the adapter."
    assert bundle["tasks"][0]["command_missing"] is True
    assert bundle["tasks"][0]["handoff"] == bundle["primary_next_task_handoff"]
    assert bundle["task_handoffs"][0]["handoff"] == bundle["primary_next_task_handoff"]

    human = runner.invoke(
        cli,
        ["cases", "--case-id", "blocked-candidate", "--evidence-bundle"],
        catch_exceptions=False,
    )

    assert human.exit_code == 0
    assert "Primary next task: `adapter_package`" in human.output
    assert "Primary next handoff: No executable command declared for `adapter_package`" in human.output
    assert "Primary incomplete task: `adapter_package`" in human.output
    assert "Blocked tasks: `1`" in human.output
    assert "Blocked task names: `metadata_validation`" in human.output


def test_cases_command_evidence_bundle_human_outputs_markdown(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cases", "--case-id", "pypi-project-search", "--evidence-bundle"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "## Evidence bundle: `pypi-project-search`" in result.output
    assert "Ready to promote: `false`" in result.output
    assert "Blocked tasks: `0`" in result.output
    assert "Incomplete tasks: `3`" in result.output
    assert "Primary next task: `adapter_package`" in result.output
    assert "Primary next command: `cliany-site explore" in result.output
    assert "Primary next handoff: Run `cliany-site explore" in result.output
    assert "## Primary next runbook" in result.output
    assert "`llm_live_preflight`: `cliany-site doctor --llm-live --json`" in result.output
    assert "`adapter_package`: `cliany-site explore" in result.output
    assert "Primary next acceptance: Attach the generated" in result.output
    assert "Primary incomplete task: `adapter_package`" in result.output
    assert "## Candidate package validation" in result.output
    assert "## LLM live preflight" in result.output
    assert "Evidence fields: `summary.ready_for_explore`, " in result.output
    assert "`summary.llm_live_preflight`" in result.output
    assert "`checks[llm_live].details.error_code`" in result.output
    assert "`checks[llm_live].details.retryable`" in result.output
    assert "`checks[llm_live].details.status_code`" in result.output
    assert "Blocker handling: Run the live LLM preflight before explore." in result.output
    assert "E_LLM_UNAVAILABLE" in result.output
    assert "## Promotion command plan" in result.output
    assert "## Acceptance criteria" in result.output
    assert "`online_smoke`: Paste the read-only adapter command JSON envelope summary" in result.output
    assert "`adapter_package` (commands.explore): `cliany-site explore" in result.output
    assert (
        "`metadata_validation` (candidate_package_validation_command): "
        "`python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict`"
        in result.output
    )
    assert (
        "`online_smoke` (commands.adapter): "
        "`cliany-site pypi.org search-projects --query cliany-site --limit 5 --json`"
        in result.output
    )
    assert (
        "python scripts/validate_cases.py --packages-dir ~/.cliany-site/packages "
        "--include-candidate-packages --strict"
        in result.output
    )
    assert "## Promotion evidence" in result.output
    assert "`adapter_package`: `pending`" in result.output
    assert "command_missing: `false`" in result.output
    assert "acceptance: Attach the generated" in result.output
    assert "handoff: Run `cliany-site explore" in result.output
    assert "cliany-site cases" not in result.output


def test_cases_command_promotion_plan_json(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--status", "candidate", "--promotion-plan"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    plan = payload["data"]["promotion_plan"]
    assert plan["candidate_count"] >= 3
    assert plan["ready_to_promote_count"] == 0
    assert plan["pending_task_count"] >= 9
    assert plan["incomplete_task_count"] >= 9
    assert plan["primary_case_id"] == "pypi-project-search"
    assert plan["primary_task"] == "adapter_package"
    assert plan["primary_command"].startswith('cliany-site explore "https://pypi.org"')
    assert plan["primary_handoff"].startswith('Run `cliany-site explore "https://pypi.org"')
    assert plan["primary_acceptance_criteria"].startswith("Attach the generated")
    assert plan["primary_runbook"] == plan["primary_next_item"]["runbook"]
    assert plan["primary_runbook"][0]["step"] == "llm_live_preflight"
    assert plan["primary_runbook"][1]["step"] == "adapter_package"
    assert plan["llm_live_preflight_command"] == "cliany-site doctor --llm-live --json"
    assert plan["primary_llm_live_preflight_command"] == plan["llm_live_preflight_command"]
    assert "E_LLM_UNAVAILABLE" in plan["llm_live_preflight_blocker_note"]
    assert "provider connection failure" in plan["llm_live_preflight_blocker_note"]
    assert (
        plan["primary_llm_live_preflight_blocker_note"]
        == plan["llm_live_preflight_blocker_note"]
    )
    assert plan["primary_next_item"] == plan["task_queue"][0]
    assert plan["primary_expected_adapter_package"] == "pypi.org-<version>.cliany-adapter.tar.gz"
    assert plan["task_queue"][0] == {
        "case_id": "pypi-project-search",
        "task": "adapter_package",
        "status": "pending",
        "expected_adapter_package": "pypi.org-<version>.cliany-adapter.tar.gz",
        "command": (
            'cliany-site explore "https://pypi.org" '
            '"search Python packages for cliany-site and list project names" --json'
        ),
        "command_source": "commands.explore",
        "command_missing": False,
        "handoff": plan["primary_handoff"],
        "acceptance_criteria": plan["primary_acceptance_criteria"],
        "runbook": plan["primary_runbook"],
        "evidence_bundle_command": "cliany-site cases --case-id pypi-project-search --evidence-bundle",
        "evidence_bundle_json_command": (
            "cliany-site cases --case-id pypi-project-search --evidence-bundle --json"
        ),
        "llm_live_preflight_command": "cliany-site doctor --llm-live --json",
        "llm_live_preflight_blocker_note": plan["llm_live_preflight_blocker_note"],
        "priority_rank": 1,
        "priority_reason": "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0",
    }
    assert plan["candidates"][0]["case_id"] == "pypi-project-search"
    assert plan["candidates"][0]["expected_adapter_package"] == (
        "pypi.org-<version>.cliany-adapter.tar.gz"
    )
    assert plan["candidates"][0]["primary_task"] == "adapter_package"
    assert plan["candidates"][0]["primary_status"] == "pending"
    assert plan["candidates"][0]["priority_rank"] == 1
    assert plan["candidates"][0]["priority_reason"] == (
        "rank 1: complete 0/3, pending 3, blocked 0, missing commands 0"
    )
    assert (
        plan["candidates"][0]["llm_live_preflight_blocker_note"]
        == plan["llm_live_preflight_blocker_note"]
    )
    assert plan["candidates"][0]["evidence_bundle_json_command"].endswith(
        "--evidence-bundle --json"
    )


def test_cases_command_promotion_plan_human_outputs_queue(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["cases", "--status", "candidate", "--promotion-plan"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "## Candidate promotion plan" in result.output
    assert "- LLM live preflight: `cliany-site doctor --llm-live --json`" in result.output
    assert "LLM blocker handling: Run the live LLM preflight before explore" in result.output
    assert "E_LLM_UNAVAILABLE" in result.output
    assert "provider connection failure" in result.output
    assert "## Primary runbook" in result.output
    assert "`llm_live_preflight`: `cliany-site doctor --llm-live --json`" in result.output
    assert "## Primary next item" in result.output
    assert "- Case: `pypi-project-search`" in result.output
    assert "- Task: `adapter_package`" in result.output
    assert (
        "Evidence bundle JSON: "
        "`cliany-site cases --case-id pypi-project-search --evidence-bundle --json`"
        in result.output
    )
    assert "## Candidate queue" in result.output
    assert "priority: `1`" in result.output
    assert "priority_reason: rank 1: complete 0/3, pending 3, blocked 0, missing commands 0" in result.output
    assert "ready_to_promote: `false`" in result.output
    assert "## Incomplete task queue" in result.output
    assert "`pypi-project-search/adapter_package` (pending)" in result.output
    assert "priority_reason: rank 1: complete 0/3, pending 3, blocked 0, missing commands 0" in result.output
    assert "acceptance: Attach the generated" in result.output


def test_cases_command_promotion_plan_prioritizes_closest_candidate(tmp_home, monkeypatch):
    import cliany_site.commands.cases as cases_module

    cases = [
        {
            "id": "empty-candidate",
            "title": "Empty candidate",
            "status": "candidate",
            "target_url": "https://empty.example/search",
            "adapter_domain": "empty.example",
            "commands": [
                'cliany-site explore "https://empty.example" "search empty" --json',
                "cliany-site empty.example search --json",
            ],
            "validation": {"offline_commands": ["python scripts/validate_cases.py --strict"]},
            "promotion": {
                "adapter_package": "Build empty.example-<version>.cliany-adapter.tar.gz.",
                "metadata_validation": "Validate the package.",
                "online_smoke": "Run the smoke command.",
            },
            "promotion_evidence": {
                "adapter_package": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Build the empty package.",
                },
                "metadata_validation": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Validate the empty package.",
                },
                "online_smoke": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Smoke the empty package.",
                },
            },
        },
        {
            "id": "nearly-ready-candidate",
            "title": "Nearly ready candidate",
            "status": "candidate",
            "target_url": "https://ready.example/search",
            "adapter_domain": "ready.example",
            "commands": [
                'cliany-site explore "https://ready.example" "search ready" --json',
                "cliany-site ready.example search --json",
            ],
            "validation": {"offline_commands": ["python scripts/validate_cases.py --strict"]},
            "promotion": {
                "adapter_package": "Build ready.example-<version>.cliany-adapter.tar.gz.",
                "metadata_validation": "Validate the package.",
                "online_smoke": "Run the smoke command.",
            },
            "promotion_evidence": {
                "adapter_package": {
                    "status": "complete",
                    "evidence": "ready.example-0.16.251.cliany-adapter.tar.gz",
                    "next_action": "",
                },
                "metadata_validation": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Validate the ready package.",
                },
                "online_smoke": {
                    "status": "pending",
                    "evidence": None,
                    "next_action": "Smoke the ready package.",
                },
            },
        },
    ]
    source = tmp_home / "cases" / "manifest.json"
    monkeypatch.setattr(cases_module, "_load_cases_manifest", lambda: (cases, source, [source]))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--status", "candidate", "--promotion-plan"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    plan = json.loads(result.output)["data"]["promotion_plan"]
    assert plan["primary_case_id"] == "nearly-ready-candidate"
    assert plan["primary_task"] == "metadata_validation"
    assert plan["primary_next_item"]["case_id"] == "nearly-ready-candidate"
    assert plan["primary_next_item"]["priority_rank"] == 1
    assert plan["primary_next_item"]["priority_reason"] == (
        "rank 1: complete 1/3, pending 2, blocked 0, missing commands 0"
    )
    assert plan["candidates"][0]["case_id"] == "nearly-ready-candidate"
    assert plan["candidates"][0]["priority_rank"] == 1
    assert plan["candidates"][0]["priority_reason"] == (
        "rank 1: complete 1/3, pending 2, blocked 0, missing commands 0"
    )
    assert plan["candidates"][1]["case_id"] == "empty-candidate"
    assert plan["candidates"][1]["priority_rank"] == 2
    assert plan["candidates"][1]["priority_reason"] == (
        "rank 2: complete 0/3, pending 3, blocked 0, missing commands 0"
    )
    assert plan["task_queue"][0]["case_id"] == "nearly-ready-candidate"
    assert plan["task_queue"][0]["task"] == "metadata_validation"
    assert plan["task_queue"][0]["priority_rank"] == 1
    assert plan["task_queue"][0]["priority_reason"] == (
        "rank 1: complete 1/3, pending 2, blocked 0, missing commands 0"
    )


def test_cases_command_issue_template_requires_case_id(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "cases", "--issue-template"], catch_exceptions=True)

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert "--issue-template / --evidence-bundle 必须配合 --case-id 使用" in payload["error"]["message"]
    assert "pypi-project-search" in payload["error"]["details"]["available_case_ids"]


def test_cases_command_evidence_bundle_requires_case_id(tmp_home):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "cases", "--evidence-bundle"], catch_exceptions=True)

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert "--issue-template / --evidence-bundle 必须配合 --case-id 使用" in payload["error"]["message"]
    assert "pypi-project-search" in payload["error"]["details"]["available_case_ids"]


def test_cases_command_rejects_issue_template_and_evidence_bundle_together(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--json",
            "cases",
            "--case-id",
            "pypi-project-search",
            "--issue-template",
            "--evidence-bundle",
        ],
        catch_exceptions=True,
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert (
        "--issue-template、--evidence-bundle 与 --promotion-plan 不能同时使用"
        in payload["error"]["message"]
    )


def test_cases_command_rejects_promotion_plan_with_other_renderers(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--json",
            "cases",
            "--case-id",
            "pypi-project-search",
            "--evidence-bundle",
            "--promotion-plan",
        ],
        catch_exceptions=True,
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert (
        "--issue-template、--evidence-bundle 与 --promotion-plan 不能同时使用"
        in payload["error"]["message"]
    )


def test_cases_command_issue_template_rejects_active_case(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--case-id", "suitecrm-accounts", "--issue-template"],
        catch_exceptions=True,
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert payload["error"]["details"]["status"] == "active"


def test_cases_command_unknown_case_returns_available_ids(tmp_home):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--json", "cases", "--status", "candidate", "--case-id", "missing"],
        catch_exceptions=True,
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_INVALID_PARAM"
    assert payload["error"]["details"]["case_id"] == "missing"
    assert payload["error"]["details"]["status_filter"] == "candidate"
    assert "pypi-project-search" in payload["error"]["details"]["available_case_ids"]


def test_cases_command_reports_missing_catalog(tmp_home, monkeypatch):
    import cliany_site.commands.cases as cases_module

    missing = tmp_home / "missing" / "manifest.json"
    monkeypatch.setattr(cases_module, "_case_catalog_paths", lambda: [missing])

    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "cases"], catch_exceptions=True)

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["command"] == "cases"
    assert payload["error"]["code"] == "E_UNKNOWN"
    assert str(Path("missing") / "manifest.json") in payload["error"]["details"]["checked_paths"][0]
