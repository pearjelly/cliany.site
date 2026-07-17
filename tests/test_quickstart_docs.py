import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "quickstart-10min.md"


def test_quickstart_documents_the_release_agnostic_first_success_path():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "pip install cliany-site",
        "cliany-site doctor",
        "cliany-site cases",
        "capabilities",
        "recommended_next_step",
        "下一步",
        "Real Demo Case Proposal",
        "cases/manifest.json",
        "cases/examples/",
        "python scripts/validate_cases.py --strict",
        "contributor-starter.md",
    ]
    for snippet in required:
        assert snippet in text

    assert "v0.14" not in text
    assert not re.search(r"\.cliany-adapter-v\d+(?:\.\d+)*(?:\.(?:tar\.gz|zip))?", text)
