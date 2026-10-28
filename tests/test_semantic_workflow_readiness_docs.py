import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROJECT_VERSION = str(tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])


@pytest.mark.parametrize("name", ["README.md", "README.zh.md", "site/docs/index.html"])
def test_semantic_readiness_docs_preserve_scope_and_fixed_trial(name):
    text = (ROOT / name).read_text()
    assert "v0.16.390" in text and "0.16.387" in text
    assert "100" in text and "10" in text
    assert "2026-10-17-semantic-workflow-readiness.md" in text


def test_semantic_readiness_release_retains_failed_studies_and_boundaries():
    text = (ROOT / "docs/releases/v0.16.390-github-release.md").read_text()
    for marker in ("# v0.16.390", "6/9", "7/9", "0/2", "DOMContentLoaded",
                   "document_not_ready", "Explicit refs", "slow images", "100-row",
                   "No guessed CSS", "Final version/master", "0.16.387"):
        assert marker in text
    evidence = (ROOT / "docs/user-evidence/2026-10-17-semantic-workflow-readiness.md").read_text()
    for marker in ("28ea0e3c4f9d321b", "57107d15223fdbb2", "16b7aff2bddeb8f4",
                   "not retrospectively", "3,734", "independent first use"):
        assert marker in evidence


def test_semantic_readiness_changelog_and_site_are_versioned():
    text = (ROOT / "CHANGELOG.md").read_text()
    assert "## [0.16.390] - 2026-10-17" in text
    assert f"[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v{PROJECT_VERSION}...HEAD" in text
    assert "[0.16.390]: https://github.com/pearjelly/cliany.site/compare/v0.16.389...v0.16.390" in text
    index = (ROOT / "site/index.html").read_text()
    script = (ROOT / "site/script.js").read_text()
    assert 'data-i18n="qs.semanticReadiness"' in index
    assert "'qs.semanticReadiness':" in script
    assert "script.js?v=20261028b" in index
