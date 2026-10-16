from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_remote_install_release_preserves_scope_and_published_baseline():
    draft = (ROOT / "docs/releases/v0.16.389-draft.md").read_text()
    notes = (ROOT / "docs/releases/v0.16.389-github-release.md").read_text()
    evidence = (ROOT / "docs/user-evidence/2026-10-17-remote-install-diagnostics.md").read_text()
    assert "# v0.16.389" in notes
    assert "v0.16.388..HEAD" in draft
    for heading in ("## 用户价值", "## 案例库映射", "## 风险与兼容性", "## 发版前验证", "## 发版步骤"):
        assert heading in draft
    for reason in ("http_error", "timeout", "tls_certificate_error", "tls_error",
                   "network_error", "incomplete_response", "download_failed"):
        assert reason in draft and reason in notes
    assert "No automatic retries" in notes
    assert "0/2" in notes and "0.16.387" in notes
    assert "failed" in evidence and "not recoverable" in evidence
    for name in ("docs/public-roadmap.md", "docs/roadmap-2026-q3.md", "docs/plans/2026-10-02-october-value-plan.md"):
        text = (ROOT / name).read_text()
        assert "0.16.389" in text and "pull/98#issuecomment-6220439464" in text


def test_remote_install_site_and_readmes_keep_trial_fixed():
    for name in ("README.md", "README.zh.md", "site/docs/index.html"):
        text = (ROOT / name).read_text()
        assert "v0.16.389" in text and "stage=download" in text
        assert "0.16.387" in text
    index = (ROOT / "site/index.html").read_text()
    script = (ROOT / "site/script.js").read_text()
    assert 'data-i18n="qs.downloadDiagnostics"' in index
    assert "'qs.downloadDiagnostics':" in script
    assert "script.js?v=20261017c" in index
    trial = (ROOT / "docs/first-use-trial.md").read_text()
    assert "cliany-site==0.16.387" in trial
    assert "cliany-site==0.16.389" not in trial


def test_remote_install_changelog_has_reviewed_range():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "## [0.16.389] - 2026-10-17" in changelog
    assert "[Unreleased]: https://github.com/pearjelly/cliany.site/compare/v0.16.390...HEAD" in changelog
    assert "[0.16.389]: https://github.com/pearjelly/cliany.site/compare/v0.16.388...v0.16.389" in changelog
