from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "release-cadence.md"


def test_release_cadence_doc_explains_readiness_triage():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "python scripts/release_readiness.py --report /tmp/cliany-release-readiness.md",
        "Gate Issues",
        "release-readiness-report",
        "next_actions",
        "先修具体 gate 失败原因",
        "python scripts/release_readiness.py --strict",
        "project_metadata",
        "package_gate",
    ]
    for snippet in required:
        assert snippet in text
