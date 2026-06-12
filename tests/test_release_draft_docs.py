from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V0144_DRAFT = ROOT / "docs" / "releases" / "v0.14.4-draft.md"
V0150_DRAFT = ROOT / "docs" / "releases" / "v0.15.0-draft.md"
V0151_DRAFT = ROOT / "docs" / "releases" / "v0.15.1-draft.md"
V0152_DRAFT = ROOT / "docs" / "releases" / "v0.15.2-draft.md"
V0153_DRAFT = ROOT / "docs" / "releases" / "v0.15.3-draft.md"
V0154_DRAFT = ROOT / "docs" / "releases" / "v0.15.4-draft.md"


def test_v0144_release_draft_has_required_sections():
    text = V0144_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.14.4 发布草案",
        "**目标版本：** `0.14.4`",
        "**提交范围：** `v0.14.3..HEAD`",
        "## 用户价值",
        "## 变更分组",
        "## 案例库映射",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
        "## Release Notes 摘要",
    ]
    for snippet in required:
        assert snippet in text


def test_v0144_release_draft_tracks_current_workstreams():
    text = V0144_DRAFT.read_text(encoding="utf-8")

    required = [
        "docs/adapter-lifecycle.md",
        "market install",
        "离线 roundtrip",
        "<domain>-<version>.cliany-adapter.tar.gz",
        "verify --json",
        "summary.recommended_next_step",
        "summary.capabilities",
        "scripts/validate_cases.py",
        "Case Catalog Validation",
        "cases/README.md",
        "cases/manifest.json",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "candidate",
        "candidate cases to declare `example_output`",
        "example_output.data.command",
        "data.quality",
        "active/candidate/known-gap/total",
        "至少保留 8 个",
        "promotion",
        "candidate `promotion` checklists",
        "Candidate Promotions",
        "search-extraction-gap",
        "docs/weekly-maintainer-loop.md",
        "docs/good-first-issues.md",
        "docs/module-ownership.md",
        "first-time contributors",
        "Issue 拆分清单",
        "website quickstart",
        "weekly maintainer loop",
        "Weekly Review",
        "Next Actions",
        "next_actions",
        "missing_commit_days",
        "release_readiness.py --json",
        "market publish` 包名",
        "python scripts/release_readiness.py --strict",
        "git tag v0.14.4",
    ]
    for snippet in required:
        assert snippet in text


def test_v0150_release_draft_has_required_sections():
    text = V0150_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.0 发布草案",
        "**目标版本：** `0.15.0`",
        "**提交范围：** `v0.14.4..HEAD`",
        "## 用户价值",
        "## 变更分组",
        "## 案例库映射",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
        "## Release Notes 摘要",
    ]
    for snippet in required:
        assert snippet in text


def test_v0150_release_draft_tracks_ten_minute_success_path():
    text = V0150_DRAFT.read_text(encoding="utf-8")

    required = [
        "10 分钟成功路径",
        "docs/quickstart-10min.md",
        "doctor",
        "data.summary.recommended_next_step",
        "data.summary.capabilities",
        "data.summary.demo_adapter_quickstart",
        "manage_adapters",
        "run_browser_workflows",
        "generate_adapters",
        "demo adapter",
        "install/list/verify",
        "Real Demo Case Proposal",
        "python scripts/release_readiness.py --target-version 0.15.0 --strict",
        "CLIANY_QA_OFFLINE=1",
        "tests/test_quickstart_docs.py",
        "tests/test_doctor_v3.py",
        "git tag v0.15.0",
    ]
    for snippet in required:
        assert snippet in text


def test_v0151_release_draft_has_required_sections():
    text = V0151_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.1 发布草案",
        "**目标版本：** `0.15.1`",
        "**提交范围：** `v0.15.0..HEAD`",
        "## 用户价值",
        "## 变更分组",
        "## 案例库映射",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
        "## Release Notes 摘要",
    ]
    for snippet in required:
        assert snippet in text


def test_v0151_release_draft_tracks_candidate_promotion_version_placeholder():
    text = V0151_DRAFT.read_text(encoding="utf-8")

    required = [
        "candidate promotion",
        "promotion.adapter_package",
        "<domain>-<version>.cliany-adapter.tar.gz",
        "market publish",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "scripts/validate_cases.py --strict",
        "release_readiness.py --target-version 0.15.1",
        "git tag v0.15.1",
    ]
    for snippet in required:
        assert snippet in text


def test_v0152_release_draft_has_required_sections():
    text = V0152_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.2 发布草案",
        "**目标版本：** `0.15.2`",
        "**提交范围：** `v0.15.1..HEAD`",
        "## 用户价值",
        "## 变更分组",
        "## 案例库映射",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
        "## Release Notes 摘要",
    ]
    for snippet in required:
        assert snippet in text


def test_v0152_release_draft_tracks_publication_audit():
    text = V0152_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/check_release_publication.py",
        "python scripts/check_release_publication.py --json",
        "python scripts/check_release_publication.py --remote --json",
        "ahead/behind",
        "tag 是否指向 HEAD",
        "next_actions",
        "git ls-remote",
        "tests/test_release_publication.py",
        "release_readiness.py --target-version 0.15.2",
        "git tag v0.15.2",
    ]
    for snippet in required:
        assert snippet in text


def test_v0153_release_draft_has_required_sections():
    text = V0153_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.3 发布草案",
        "**目标版本：** `0.15.3`",
        "**提交范围：** `v0.15.2..HEAD`",
        "## 用户价值",
        "## 变更分组",
        "## 案例库映射",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
        "## Release Notes 摘要",
    ]
    for snippet in required:
        assert snippet in text


def test_v0153_release_draft_tracks_publication_markdown_report():
    text = V0153_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/check_release_publication.py",
        "--report /tmp/cliany-release-publication.md",
        "Summary",
        "Refs",
        "Next Actions",
        "next_actions",
        "remote branch HEAD",
        "remote tag commit",
        "release-readiness-report.md",
        "release_readiness.py --target-version 0.15.3",
        "git tag v0.15.3",
    ]
    for snippet in required:
        assert snippet in text


def test_v0154_release_draft_has_required_sections():
    text = V0154_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.4 发布草案",
        "**目标版本：** `0.15.4`",
        "**提交范围：** `v0.15.3..HEAD`",
        "## 用户价值",
        "## 变更分组",
        "## 案例库映射",
        "cases/README.md",
        "cases/manifest.json",
        "## 风险与兼容性",
        "## 发版前验证",
        "## 发版步骤",
        "## Release Notes 摘要",
    ]
    for snippet in required:
        assert snippet in text


def test_v0154_release_draft_tracks_readme_publication_entrypoint():
    text = V0154_DRAFT.read_text(encoding="utf-8")

    required = [
        "README.md",
        "README.zh.md",
        "scripts/check_release_publication.py --json",
        "最新本地 tag 是否公开可见",
        "tests/test_readme_current_features.py",
        "release_readiness.py --target-version 0.15.4",
        "git tag v0.15.4",
    ]
    for snippet in required:
        assert snippet in text
