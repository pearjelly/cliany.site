from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "contributor-starter.md"
GOOD_FIRST = ROOT / "docs" / "good-first-issues.md"
OWNERSHIP = ROOT / "docs" / "module-ownership.md"


def test_contributor_starter_doc_has_required_sections():
    text = DOC.read_text(encoding="utf-8")

    required_headings = [
        "## Good First Issues",
        "## Issue 与 PR 模板",
        "## 模块地图",
        "## 复现问题的最小包",
        "## PR 验证策略",
        "## 贡献边界",
    ]
    for heading in required_headings:
        assert heading in text


def test_contributor_starter_referenced_paths_exist():
    paths = [
        "cases",
        "docs",
        "src/cliany_site/commands/doctor.py",
        "scripts/release_readiness.py",
        "scripts/check_release_cadence.py",
        "scripts/check_release_publication.py",
        "docs/good-first-issues.md",
        "docs/module-ownership.md",
        "tests/test_cases_manifest.py",
        "tests/test_release_readiness.py",
        "tests/test_release_cadence.py",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
    ]
    for path in paths:
        assert (ROOT / path).exists(), f"missing referenced path: {path}"


def test_contributor_starter_uses_release_readiness_as_release_entrypoint():
    text = DOC.read_text(encoding="utf-8")

    assert "python scripts/release_readiness.py --json" in text
    assert "python scripts/check_release_publication.py --json --report /tmp/cliany-release-publication.md" in text
    assert (
        "pytest tests/test_release_readiness.py tests/test_release_cadence.py tests/test_release_publication.py "
        "-q --no-cov"
    ) in text


def test_contributor_starter_points_to_issue_and_pr_templates():
    text = DOC.read_text(encoding="utf-8")

    required = [
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "doctor --json",
        "AXTree snapshot",
        "离线 JSON envelope 样例",
        "Candidate Promotion Tasks",
        "Issue Body Template",
        "Reproduction Context",
        "Evidence Bundle",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "CLIANY_QA_OFFLINE=1",
    ]
    for snippet in required:
        assert snippet in text


def test_contributor_starter_links_module_ownership_map():
    text = DOC.read_text(encoding="utf-8")

    assert "module-ownership.md" in text
    assert "模块 Ownership 与验证地图" in text


def test_module_ownership_doc_maps_owner_areas_to_validation():
    text = OWNERSHIP.read_text(encoding="utf-8")

    required = [
        "# 模块 Ownership 与验证地图",
        "Owner area",
        "CLI contract",
        "First-run diagnostics",
        "Browser and replay runtime",
        "Adapter lifecycle",
        "Case catalog",
        "Release operations",
        "scripts/check_release_publication.py",
        "Contributor experience",
        "Website and public docs",
        "CLIANY_QA_OFFLINE=1",
        "python scripts/validate_cases.py --strict",
        "pytest tests/test_release_readiness.py tests/test_release_cadence.py tests/test_release_publication.py "
        "-q --no-cov",
        "Owner area:",
        "Risk boundary:",
        "~/.cliany-site/",
    ]
    for snippet in required:
        assert snippet in text


def test_good_first_issues_doc_is_offline_and_verifiable():
    text = GOOD_FIRST.read_text(encoding="utf-8")

    required = [
        "# Good First Issues",
        "CLIANY_QA_OFFLINE=1",
        "python scripts/validate_cases.py --strict",
        "python scripts/validate_cases.py --json",
        "python scripts/validate_cases.py --report /tmp/cliany-case-catalog-report.md",
        "python scripts/release_readiness.py",
        "promotion",
        "Candidate Promotion Tasks",
        "Issue Body Template",
        "Reproduction Context",
        "Evidence Bundle",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "~/.cliany-site/",
        "不需要真实 LLM key",
    ]
    for snippet in required:
        assert snippet in text
