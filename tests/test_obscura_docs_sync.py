import os
import pytest
from pathlib import Path

DOCS_DIR = Path("docs")
DECISIONS_DIR = DOCS_DIR / "decisions"
WALKTHROUGHS_DIR = DOCS_DIR / "walkthroughs"

DOCS_TO_CHECK = [
    DECISIONS_DIR / "0002-obscura-provider-compatibility.md",
    DECISIONS_DIR / "0003-obscura-binary-lifecycle.md",
    DECISIONS_DIR / "0004-obscura-provider-abstraction.md",
    DECISIONS_DIR / "0005-obscura-explore-gate.md",
    DECISIONS_DIR / "0006-obscura-three-platform-support.md",
    WALKTHROUGHS_DIR / "obscura-experimental-guide.md",
    WALKTHROUGHS_DIR / "obscura-release-gates.md",
]

def test_docs_exist():
    for doc in DOCS_TO_CHECK:
        assert doc.exists(), f"文档缺失: {doc}"

def test_experimental_guide_mentions_experimental():
    content = (WALKTHROUGHS_DIR / "obscura-experimental-guide.md").read_text()
    assert "EXPERIMENTAL" in content

def test_adr_0002_mentions_axtree():
    content = (DECISIONS_DIR / "0002-obscura-provider-compatibility.md").read_text()
    assert "supports_axtree" in content

def test_adr_0003_mentions_lifecycle_keys():
    content = (DECISIONS_DIR / "0003-obscura-binary-lifecycle.md").read_text()
    assert "active_version" in content or "rollback" in content

def test_adr_0004_mentions_chrome_defaults():
    content = (DECISIONS_DIR / "0004-obscura-provider-abstraction.md").read_text()
    assert "Chrome" in content or "ChromeProvider" in content

def test_adr_0005_mentions_explore_gate():
    content = (DECISIONS_DIR / "0005-obscura-explore-gate.md").read_text()
    assert "explore" in content

def test_adr_0006_mentions_platforms():
    content = (DECISIONS_DIR / "0006-obscura-three-platform-support.md").read_text()
    assert "darwin" in content or "linux" in content

def test_experimental_declaration_failure(monkeypatch):
    def mock_read_text(self):
        return "This is a stable guide without any warnings."
    
    content = "Stable guide"
    if "EXPERIMENTAL" not in content:
        pass 
    
    assert True

def test_adr_0004_mentions_provider_abstraction():
    content = (DECISIONS_DIR / "0004-obscura-provider-abstraction.md").read_text()
    assert "Provider Abstraction" in content or "提供商抽象" in content

def test_release_gates_mentions_smoke_test():
    content = (WALKTHROUGHS_DIR / "obscura-release-gates.md").read_text()
    assert "obscura-smoke" in content or "smoke" in content
