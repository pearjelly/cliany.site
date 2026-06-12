from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "case_proposal.yml"
ISSUE_CONFIG = ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
PR_TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"


def test_case_proposal_issue_template_collects_verifiable_case_details():
    text = CASE_TEMPLATE.read_text(encoding="utf-8")

    required = [
        'labels: ["case-proposal"]',
        "id: scenario",
        "id: target_url",
        "id: workflow",
        "id: expected_command",
        "id: example_output",
        "id: validation",
        "id: promotion",
        "Candidate Promotion Tasks",
        "Issue Body Template",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "python scripts/validate_cases.py --strict",
        "cases/manifest.json",
        "cases/examples/",
        "只读",
        "敏感信息",
        "degraded",
    ]
    for snippet in required:
        assert snippet in text


def test_pull_request_template_routes_validation_by_change_type():
    text = PR_TEMPLATE.read_text(encoding="utf-8")

    required = [
        "python scripts/validate_cases.py --strict",
        "python scripts/release_readiness.py --json",
        "CLIANY_QA_OFFLINE=1",
        "CHANGELOG 或 release draft",
        "~/.cliany-site/",
        "已按改动风险选择验证范围",
    ]
    for snippet in required:
        assert snippet in text


def test_issue_template_config_routes_security_reports_privately():
    text = ISSUE_CONFIG.read_text(encoding="utf-8")

    required = [
        "blank_issues_enabled: false",
        "Documentation",
        "security/advisories/new",
    ]
    for snippet in required:
        assert snippet in text
