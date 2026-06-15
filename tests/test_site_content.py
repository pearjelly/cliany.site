from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_site_quickstart_matches_v0150_ten_minute_success_path():
    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    docs = (ROOT / "site" / "docs" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "script.js").read_text(encoding="utf-8")

    assert "cliany-site doctor" in index
    assert "10-Minute Success Path" in index
    assert "10 分钟成功路径" in docs
    assert "issues.apache.org.cliany-adapter-v0.14.0.tar.gz" in index
    assert "issues.apache.org.cliany-adapter-v0.14.0.tar.gz" in docs
    assert "cliany-site verify issues.apache.org --json" in index
    assert "cliany-site verify issues.apache.org --json" in docs
    assert "cliany-site issues.apache.org list-issues --project SPARK --limit 5 --json" in docs
    assert "不需要先配置 LLM key" in docs
    assert "Real Demo Case Proposal" in index
    assert "cases/manifest.json" in index
    assert "python scripts/validate_cases.py --strict" in index
    assert "cliany-site cases --case-id pypi-project-search --evidence-bundle --json" in index
    assert "docs/good-first-issues.md" in index
    assert "docs/weekly-maintainer-loop.md" in index
    assert "python scripts/release_readiness.py --json" in index
    assert "python scripts/check_release_cadence.py --json" in index
    assert "next_actions" in index
    assert "10-Minute Success Path" in script
    assert "Run a real demo adapter first" in script
    assert "Generate Your Own" in script
    assert "After Your First Success" in script
    assert "First-time contributors" in script
    assert "Maintainer Loop" in script
