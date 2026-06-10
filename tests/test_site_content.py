from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_site_quickstart_matches_v0143_first_run_path():
    index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "script.js").read_text(encoding="utf-8")

    assert "cliany-site doctor" in index
    assert "issues.apache.org.cliany-adapter-v0.14.0.tar.gz" in index
    assert "cliany-site verify issues.apache.org --json" in index
    assert "Real Demo Case Proposal" in index
    assert "cases/manifest.json" in index
    assert "python scripts/validate_cases.py --strict" in index
    assert "Run a real demo first" in script
    assert "Generate Your Own" in script
    assert "After Your First Success" in script
