import json
from pathlib import Path

from click.testing import CliRunner

from cliany_site.cli import cli


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
    assert "Generate pypi.org" in data["promotion_evidence_summary"]["primary_next_action"]
    assert {case["status"] for case in data["cases"]} == {"candidate"}
    assert all("promotion" in case for case in data["cases"])
    assert all("promotion_evidence" in case for case in data["cases"])


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
    }
    assert "## Scope: promote candidate case `pypi-project-search`" in template
    assert "## Primary Evidence Task" in template
    assert "- Task: `adapter_package`" in template
    assert "- Status: `pending`" in template
    assert "## Reproduction Context" in template
    assert "`adapter_package`" in template
    assert "Generate pypi.org" in template
    assert "## Evidence Bundle" in template
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle" in template
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in template
    assert "Attach or paste the JSON output in the issue once evidence changes." in template
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
    }
    assert "## Primary Evidence Task" in result.output
    assert "- Task: `online_smoke`" in result.output
    assert "- Status: `pending`" in result.output
    assert "- Next action: Run read-only smoke." in result.output
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
    assert bundle["primary_next_action"].startswith("Generate pypi.org")
    assert bundle["tasks"][0]["task"] == "adapter_package"
    assert bundle["tasks"][0]["complete"] is False
    assert "python scripts/validate_cases.py --strict" in bundle["offline_commands"]


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
    assert bundle["pending_task_count"] == 1
    assert bundle["blocked_task_count"] == 1
    assert bundle["complete_task_count"] == 1
    assert bundle["incomplete_task_count"] == 2
    assert bundle["ready_to_promote"] is False
    assert bundle["primary_next_action"] == "Package the adapter."

    human = runner.invoke(
        cli,
        ["cases", "--case-id", "blocked-candidate", "--evidence-bundle"],
        catch_exceptions=False,
    )

    assert human.exit_code == 0
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
    assert "Primary incomplete task: `adapter_package`" in result.output
    assert "## Promotion evidence" in result.output
    assert "`adapter_package`: `pending`" in result.output
    assert "cliany-site cases" not in result.output


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
    assert "--issue-template 与 --evidence-bundle 不能同时使用" in payload["error"]["message"]


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
