from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V0144_DRAFT = ROOT / "docs" / "releases" / "v0.14.4-draft.md"
V0150_DRAFT = ROOT / "docs" / "releases" / "v0.15.0-draft.md"
V0151_DRAFT = ROOT / "docs" / "releases" / "v0.15.1-draft.md"
V0152_DRAFT = ROOT / "docs" / "releases" / "v0.15.2-draft.md"
V0153_DRAFT = ROOT / "docs" / "releases" / "v0.15.3-draft.md"
V0154_DRAFT = ROOT / "docs" / "releases" / "v0.15.4-draft.md"
V0155_DRAFT = ROOT / "docs" / "releases" / "v0.15.5-draft.md"
V0156_DRAFT = ROOT / "docs" / "releases" / "v0.15.6-draft.md"
V0157_DRAFT = ROOT / "docs" / "releases" / "v0.15.7-draft.md"
V0158_DRAFT = ROOT / "docs" / "releases" / "v0.15.8-draft.md"
V0159_DRAFT = ROOT / "docs" / "releases" / "v0.15.9-draft.md"
V0160_DRAFT = ROOT / "docs" / "releases" / "v0.16.0-draft.md"
V0161_DRAFT = ROOT / "docs" / "releases" / "v0.16.1-draft.md"
V0162_DRAFT = ROOT / "docs" / "releases" / "v0.16.2-draft.md"
V0163_DRAFT = ROOT / "docs" / "releases" / "v0.16.3-draft.md"
V0164_DRAFT = ROOT / "docs" / "releases" / "v0.16.4-draft.md"
V0165_DRAFT = ROOT / "docs" / "releases" / "v0.16.5-draft.md"
V0166_DRAFT = ROOT / "docs" / "releases" / "v0.16.6-draft.md"
V0167_DRAFT = ROOT / "docs" / "releases" / "v0.16.7-draft.md"
V0168_DRAFT = ROOT / "docs" / "releases" / "v0.16.8-draft.md"
V0169_DRAFT = ROOT / "docs" / "releases" / "v0.16.9-draft.md"
V01610_DRAFT = ROOT / "docs" / "releases" / "v0.16.10-draft.md"
V01611_DRAFT = ROOT / "docs" / "releases" / "v0.16.11-draft.md"
V01612_DRAFT = ROOT / "docs" / "releases" / "v0.16.12-draft.md"


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


def test_v0155_release_draft_has_required_sections():
    text = V0155_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.5 发布草案",
        "**目标版本：** `0.15.5`",
        "**提交范围：** `v0.15.4..HEAD`",
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


def test_v0155_release_draft_tracks_module_ownership_publication_entrypoint():
    text = V0155_DRAFT.read_text(encoding="utf-8")

    required = [
        "docs/module-ownership.md",
        "Release operations",
        "scripts/check_release_publication.py",
        "tests/test_release_publication.py",
        "tests/test_contributor_docs.py",
        "release_readiness.py --target-version 0.15.5",
        "git tag v0.15.5",
    ]
    for snippet in required:
        assert snippet in text


def test_v0156_release_draft_has_required_sections():
    text = V0156_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.6 发布草案",
        "**目标版本：** `0.15.6`",
        "**提交范围：** `v0.15.5..HEAD`",
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


def test_v0156_release_draft_tracks_candidate_promotion_task_split():
    text = V0156_DRAFT.read_text(encoding="utf-8")

    required = [
        "candidate 晋级",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "docs/good-first-issues.md",
        "tests/test_good_first_issues_docs.py",
        "python scripts/validate_cases.py --strict",
        "release_readiness.py --target-version 0.15.6",
        "git tag v0.15.6",
    ]
    for snippet in required:
        assert snippet in text


def test_v0157_release_draft_has_required_sections():
    text = V0157_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.7 发布草案",
        "**目标版本：** `0.15.7`",
        "**提交范围：** `v0.15.6..HEAD`",
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


def test_v0157_release_draft_tracks_candidate_promotion_report_tasks():
    text = V0157_DRAFT.read_text(encoding="utf-8")

    required = [
        "Candidate Promotion Tasks",
        "scripts/validate_cases.py --report",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "data.quality.ok=true",
        "row_count>0",
        "tests/test_validate_cases.py",
        "release_readiness.py --target-version 0.15.7",
        "git tag v0.15.7",
    ]
    for snippet in required:
        assert snippet in text


def test_v0158_release_draft_has_required_sections():
    text = V0158_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.8 发布草案",
        "**目标版本：** `0.15.8`",
        "**提交范围：** `v0.15.7..HEAD`",
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


def test_v0158_release_draft_tracks_candidate_issue_body_templates():
    text = V0158_DRAFT.read_text(encoding="utf-8")

    required = [
        "Issue Body Template",
        "Candidate Promotion Tasks",
        "Validation Evidence",
        "Non-goals",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "不要提前把案例改成 `active`",
        "真实 LLM key",
        "tests/test_validate_cases.py",
        "release_readiness.py --target-version 0.15.8",
        "git tag v0.15.8",
    ]
    for snippet in required:
        assert snippet in text


def test_v0159_release_draft_has_required_sections():
    text = V0159_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.15.9 发布草案",
        "**目标版本：** `0.15.9`",
        "**提交范围：** `v0.15.8..HEAD`",
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


def test_v0159_release_draft_tracks_case_proposal_promotion_evidence():
    text = V0159_DRAFT.read_text(encoding="utf-8")

    required = [
        "Real Demo Case Proposal",
        ".github/ISSUE_TEMPLATE/case_proposal.yml",
        "promotion",
        "Candidate Promotion Tasks",
        "Issue Body Template",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "docs/contributor-starter.md",
        "tests/test_issue_templates.py",
        "release_readiness.py --target-version 0.15.9",
        "git tag v0.15.9",
    ]
    for snippet in required:
        assert snippet in text


def test_v0160_release_draft_has_required_sections():
    text = V0160_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.0 发布草案",
        "**目标版本：** `0.16.0`",
        "**提交范围：** `v0.15.9..HEAD`",
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


def test_v0160_release_draft_tracks_structured_offline_validation_commands():
    text = V0160_DRAFT.read_text(encoding="utf-8")

    required = [
        "validation.offline_commands",
        "Offline Validation Commands",
        "scripts/validate_cases.py --report",
        "tests/test_cases_manifest.py",
        "tests/test_validate_cases.py",
        "python scripts/release_readiness.py --target-version 0.16.0",
        "git tag v0.16.0",
    ]
    for snippet in required:
        assert snippet in text


def test_v0161_release_draft_has_required_sections():
    text = V0161_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.1 发布草案",
        "**目标版本：** `0.16.1`",
        "**提交范围：** `v0.16.0..HEAD`",
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


def test_v0161_release_draft_tracks_package_validation_next_actions():
    text = V0161_DRAFT.read_text(encoding="utf-8")

    required = [
        "next_actions",
        "domain mismatch",
        "metadata schema",
        "manifest hash",
        "missing package",
        "tests/test_validate_cases.py",
        "python scripts/release_readiness.py --target-version 0.16.1",
        "git tag v0.16.1",
    ]
    for snippet in required:
        assert snippet in text


def test_v0162_release_draft_has_required_sections():
    text = V0162_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.2 发布草案",
        "**目标版本：** `0.16.2`",
        "**提交范围：** `v0.16.1..HEAD`",
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


def test_v0162_release_draft_tracks_next_iteration_planner():
    text = V0162_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "release_readiness.py",
        "check_release_publication.py",
        "commit days",
        "candidate cases",
        "recommended_theme",
        "recommended_slice",
        "next_actions",
        "validation_commands",
        "release_draft_path",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.2 --json",
        "git tag v0.16.2",
    ]
    for snippet in required:
        assert snippet in text


def test_v0163_release_draft_has_required_sections():
    text = V0163_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.3 发布草案",
        "**目标版本：** `0.16.3`",
        "**提交范围：** `v0.16.2..HEAD`",
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


def test_v0163_release_draft_tracks_candidate_promotion_planning():
    text = V0163_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "candidate_promotions",
        "Candidate Promotion Tasks",
        "adapter_package",
        "metadata_validation",
        "online_smoke",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.3 --json",
        "git tag v0.16.3",
    ]
    for snippet in required:
        assert snippet in text


def test_v0164_release_draft_has_required_sections():
    text = V0164_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.4 发布草案",
        "**目标版本：** `0.16.4`",
        "**提交范围：** `v0.16.3..HEAD`",
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


def test_v0164_release_draft_tracks_candidate_issue_body_templates():
    text = V0164_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "candidate_promotions",
        "issue_body",
        "Candidate Issue Body Templates",
        "Scope",
        "Tasks",
        "Validation Evidence",
        "Non-goals",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.4 --json",
        "git tag v0.16.4",
    ]
    for snippet in required:
        assert snippet in text


def test_v0165_release_draft_has_required_sections():
    text = V0165_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.5 发布草案",
        "**目标版本：** `0.16.5`",
        "**提交范围：** `v0.16.4..HEAD`",
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


def test_v0165_release_draft_tracks_candidate_issue_metadata():
    text = V0165_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "candidate_promotions",
        "issue_title",
        "issue_labels",
        "Candidate Issue Metadata",
        "Candidate Issue Body Templates",
        "case-proposal",
        "good first issue",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.5 --json",
        "git tag v0.16.5",
    ]
    for snippet in required:
        assert snippet in text


def test_v0166_release_draft_has_required_sections():
    text = V0166_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.6 发布草案",
        "**目标版本：** `0.16.6`",
        "**提交范围：** `v0.16.5..HEAD`",
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


def test_v0166_release_draft_tracks_candidate_issue_artifacts():
    text = V0166_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "--issues-dir",
        "issue-metadata.json",
        "create-issues.sh",
        "gh issue create",
        "issue_body_file",
        "create_command",
        "pypi-project-search.md",
        "npm-package-search.md",
        "crates-io-crate-search.md",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.6 --issues-dir",
        "git tag v0.16.6",
    ]
    for snippet in required:
        assert snippet in text


def test_v0167_release_draft_has_required_sections():
    text = V0167_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.7 发布草案",
        "**目标版本：** `0.16.7`",
        "**提交范围：** `v0.16.6..HEAD`",
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


def test_v0167_release_draft_tracks_candidate_issue_artifact_readme():
    text = V0167_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "--issues-dir",
        "README.md",
        "issue-metadata.json",
        "create-issues.sh",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "审阅清单",
        "不会由计划器自动执行",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.7 --issues-dir",
        "git tag v0.16.7",
    ]
    for snippet in required:
        assert snippet in text


def test_v0168_release_draft_has_required_sections():
    text = V0168_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.8 发布草案",
        "**目标版本：** `0.16.8`",
        "**提交范围：** `v0.16.7..HEAD`",
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


def test_v0168_release_draft_tracks_issue_artifacts_regeneration_command():
    text = V0168_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "issue_artifacts_command",
        "--issues-dir",
        "/tmp/cliany-candidate-issues",
        "README.md",
        "issue-metadata.json",
        "create-issues.sh",
        "复现命令",
        "pypi-project-search",
        "npm-package-search",
        "crates-io-crate-search",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.8 --issues-dir",
        "git tag v0.16.8",
    ]
    for snippet in required:
        assert snippet in text


def test_v0169_release_draft_has_required_sections():
    text = V0169_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.9 发布草案",
        "**目标版本：** `0.16.9`",
        "**提交范围：** `v0.16.8..HEAD`",
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


def test_v0169_release_draft_tracks_publication_publish_commands():
    text = V0169_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/check_release_publication.py",
        "publish_commands",
        "git push origin master",
        "git push origin v0.16.9",
        "python scripts/check_release_publication.py --remote --json",
        "## Publish Commands",
        "tests/test_release_publication.py",
        "tests/test_release_cadence_docs.py",
        "tests/test_release_draft_docs.py",
        "python scripts/check_release_publication.py --json --report",
        "python scripts/release_readiness.py --target-version 0.16.9 --json",
        "git tag v0.16.9",
    ]
    for snippet in required:
        assert snippet in text


def test_v01610_release_draft_has_required_sections():
    text = V01610_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.10 发布草案",
        "**目标版本：** `0.16.10`",
        "**提交范围：** `v0.16.9..HEAD`",
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


def test_v01610_release_draft_tracks_plan_publication_publish_commands():
    text = V01610_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "publication_publish_commands",
        "publish_commands",
        "Publication Publish Commands",
        "git push origin master",
        "git push origin v0.16.9",
        "python scripts/check_release_publication.py --remote --json",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "tests/test_release_draft_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.10 --json",
        "git tag v0.16.10",
    ]
    for snippet in required:
        assert snippet in text


def test_v01611_release_draft_has_required_sections():
    text = V01611_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.11 发布草案",
        "**目标版本：** `0.16.11`",
        "**提交范围：** `v0.16.10..HEAD`",
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


def test_v01611_release_draft_tracks_publication_publish_script():
    text = V01611_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/check_release_publication.py",
        "--publish-script",
        "/tmp/cliany-publish-release.sh",
        "publish_commands",
        "git push origin master",
        "git push origin v0.16.11",
        "python scripts/check_release_publication.py --remote --json",
        "chmod",
        "tests/test_release_publication.py",
        "tests/test_release_cadence_docs.py",
        "tests/test_release_draft_docs.py",
        "python scripts/check_release_publication.py --json --publish-script",
        "python scripts/release_readiness.py --target-version 0.16.11 --json",
        "git tag v0.16.11",
    ]
    for snippet in required:
        assert snippet in text


def test_v01612_release_draft_has_required_sections():
    text = V01612_DRAFT.read_text(encoding="utf-8")

    required = [
        "# v0.16.12 发布草案",
        "**目标版本：** `0.16.12`",
        "**提交范围：** `v0.16.11..HEAD`",
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


def test_v01612_release_draft_tracks_plan_publication_publish_script_command():
    text = V01612_DRAFT.read_text(encoding="utf-8")

    required = [
        "scripts/plan_next_iteration.py",
        "publication_publish_script_command",
        "--publish-script /tmp/cliany-publish-release.sh",
        "Publication Publish Script",
        "publication_publish_commands",
        "python scripts/check_release_publication.py --json --publish-script",
        "tests/test_plan_next_iteration.py",
        "tests/test_weekly_maintainer_loop_docs.py",
        "tests/test_release_draft_docs.py",
        "python scripts/plan_next_iteration.py --target-version 0.16.12 --json",
        "git tag v0.16.12",
    ]
    for snippet in required:
        assert snippet in text
