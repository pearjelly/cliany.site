from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs" / "releases" / "v0.14.4-draft.md"


def test_v0144_release_draft_has_required_sections():
    text = DRAFT.read_text(encoding="utf-8")

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
    text = DRAFT.read_text(encoding="utf-8")

    required = [
        "docs/adapter-lifecycle.md",
        "market install",
        "verify --json",
        "scripts/validate_cases.py",
        "Case Catalog Validation",
        "cases/README.md",
        "cases/manifest.json",
        "search-extraction-gap",
        "python scripts/release_readiness.py --strict",
        "git tag v0.14.4",
    ]
    for snippet in required:
        assert snippet in text
