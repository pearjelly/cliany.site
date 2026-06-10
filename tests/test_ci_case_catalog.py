from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_runs_case_catalog_validation():
    text = CI.read_text(encoding="utf-8")

    required = [
        "case-catalog:",
        "Case Catalog Validation",
        "CLIANY_QA_OFFLINE",
        "python scripts/validate_cases.py --strict --report case-catalog-report.md",
        "pytest tests/test_validate_cases.py tests/test_cases_manifest.py -q --no-cov",
        "case-catalog-report",
        "case-catalog-report.md",
    ]
    for snippet in required:
        assert snippet in text
