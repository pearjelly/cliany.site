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
    assert "docs/good-first-issues.md" in index
    assert "docs/weekly-maintainer-loop.md" in index
    assert "python scripts/release_readiness.py --json" in index
    assert "python scripts/check_release_cadence.py --json" in index
    assert "next_actions" in index
    assert "Run a real demo first" in script
    assert "Generate Your Own" in script
    assert "After Your First Success" in script
    assert "First-time contributors" in script
    assert "Maintainer Loop" in script
