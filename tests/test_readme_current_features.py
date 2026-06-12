from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readmes_document_current_extract_quality_and_readiness():
    expected_partial_terms = {
        "README.md": "partially missing required fields",
        "README.zh.md": "关键字段部分缺失",
    }
    for filename in ("README.md", "README.zh.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")

        assert "v0.14.4" in text
        assert "data.quality" in text
        assert "--strict-quality" in text
        assert "E_EMPTY_RESULT" in text
        assert "scripts/release_readiness.py" in text
        assert "scripts/check_release_publication.py --json" in text
        assert "Real Demo Case Proposal" in text
        assert "weekly-maintainer-loop.md" in text
        assert "next_actions" in text
        assert "github.com-1.0.0.cliany-adapter.tar.gz" in text
        assert "./github.com.cliany-adapter.tar.gz" not in text
        assert expected_partial_terms[filename] in text
