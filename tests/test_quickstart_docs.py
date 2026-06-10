from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "quickstart-10min.md"


def test_quickstart_links_first_success_to_case_contribution_path():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "cliany-site doctor",
        "recommended_next_step",
        "下一步",
        "cliany-site verify issues.apache.org --json",
        "Real Demo Case Proposal",
        "cases/manifest.json",
        "cases/examples/",
        "python scripts/validate_cases.py --strict",
        "contributor-starter.md",
    ]
    for snippet in required:
        assert snippet in text
