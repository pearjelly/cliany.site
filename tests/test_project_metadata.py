import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_has_pypi_description():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert project["description"]
    readme = project["readme"]
    assert readme == "README.md"
    assert (ROOT / readme).exists()


def test_project_has_open_source_metadata_files():
    for filename in (
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "SUPPORT.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    ):
        assert (ROOT / filename).exists(), f"{filename} is required for open source readiness"


def test_readmes_have_open_source_entrypoints():
    for filename in ("README.md", "README.zh.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")

        assert "scripts/release_readiness.py" in text
        assert "Real Demo Case Proposal" in text
        assert "data.quality" in text
