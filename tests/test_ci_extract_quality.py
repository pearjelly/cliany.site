from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_runs_extract_quality_regression():
    text = CI.read_text(encoding="utf-8")

    required = [
        "extract-quality:",
        "Extract Quality Regression",
        "CLIANY_QA_OFFLINE",
        "tests/test_extract_quality.py",
        "tests/test_extract_writer_quality.py",
        "tests/test_runtime_helpers_extract_quality.py",
        "tests/test_browser_part_c.py",
        "tests/test_generated_orchestration.py",
    ]
    for snippet in required:
        assert snippet in text
