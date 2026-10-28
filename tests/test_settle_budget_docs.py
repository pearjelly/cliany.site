from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_budget_release_documents_bound_scope_and_retained_failures():
    notes = (ROOT / "docs/releases/v0.16.388-github-release.md").read_text()
    draft = (ROOT / "docs/releases/v0.16.388-draft.md").read_text()
    evidence = (ROOT / "docs/user-evidence/2026-10-17-list-settle-budget.md").read_text()
    assert "# v0.16.388" in notes
    for reason in ("settle_probe_failed", "settle_probe_invalid", "settle_probe_timeout", "list_unsettled"):
        assert reason in notes and reason in draft
    assert "not a complete-command deadline" in notes
    assert "prior coarser error contract" in notes
    assert "v0.16.387..HEAD" in draft
    for heading in ("## 案例库映射", "## 风险与兼容性", "## 发版前验证", "## 发版步骤"):
        assert heading in draft
    assert "0/2" in notes and "0/2" in draft
    assert "10" in evidence and "failed" in evidence
    assert "no release was backdated" in evidence


def test_budget_website_and_readmes_keep_trial_version_fixed():
    for name in ("README.md", "README.zh.md", "site/docs/index.html"):
        text = (ROOT / name).read_text()
        assert "v0.16.388" in text
        assert "settle_probe_timeout" in text
        assert "0.16.387" in text
    index = (ROOT / "site/index.html").read_text()
    script = (ROOT / "site/script.js").read_text()
    assert 'data-i18n="qs.settleBudget"' in index
    assert "'qs.settleBudget':" in script
    assert "script.js?v=20261028c" in index
    guide = (ROOT / "docs/first-use-trial.md").read_text()
    assert "cliany-site==0.16.387" in guide
    assert "cliany-site==0.16.388" not in guide


def test_roadmaps_point_to_published_v387_receipt_and_v388_candidate():
    for name in ("docs/public-roadmap.md", "docs/roadmap-2026-q3.md", "docs/plans/2026-10-02-october-value-plan.md"):
        text = (ROOT / name).read_text()
        assert "0.16.388" in text
        assert "pull/97#issuecomment-6188983342" in text
        assert "0/2" in text
