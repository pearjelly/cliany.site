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
    assert "pypi-project-search" in result.output
    assert "cliany-site explore" in result.output
    assert "cliany-site pypi.org search-projects --query cliany-site --limit 5 --json" in result.output
    assert "python scripts/validate_cases.py --strict" in result.output


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
