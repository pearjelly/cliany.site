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
        "docs/good-first-issues.md",
        "docs/module-ownership.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
    ):
        assert (ROOT / filename).exists(), f"{filename} is required for open source readiness"


def test_direct_runtime_imports_are_declared_as_dependencies():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = data["project"]["dependencies"]

    assert "aiohttp" in dependencies
    assert "PyYAML" in dependencies


def test_security_policy_tracks_latest_stable_release():
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert "Latest stable release" in policy
    assert "Earlier releases" in policy
    assert "0.6.x" not in policy


def test_readmes_have_open_source_entrypoints():
    for filename in ("README.md", "README.zh.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")

        assert "scripts/release_readiness.py" in text
        assert "Real Demo Case Proposal" in text
        assert "docs/good-first-issues.md" in text
        assert "data.quality" in text
