from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "case_proposal.yml"


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
        "python scripts/validate_cases.py --strict",
        "cases/manifest.json",
        "cases/examples/",
        "只读",
        "敏感信息",
        "degraded",
    ]
    for snippet in required:
        assert snippet in text
