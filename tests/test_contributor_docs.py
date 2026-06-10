from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "contributor-starter.md"


def test_contributor_starter_doc_has_required_sections():
    text = DOC.read_text(encoding="utf-8")

    required_headings = [
        "## Good First Issues",
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
        "scripts/check_release_cadence.py",
        "tests/test_cases_manifest.py",
        "tests/test_release_cadence.py",
    ]
    for path in paths:
        assert (ROOT / path).exists(), f"missing referenced path: {path}"

