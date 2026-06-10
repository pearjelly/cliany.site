from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "adapter-lifecycle.md"


def test_adapter_lifecycle_doc_has_required_sections():
    text = DOC.read_text(encoding="utf-8")

    required_headings = [
        "## 生命周期总览",
        "## 运行时位置",
        "## 包格式",
        "## 兼容性矩阵",
        "## 安全边界",
        "## 维护流程",
        "## 贡献入口",
    ]
    for heading in required_headings:
        assert heading in text


def test_adapter_lifecycle_doc_pins_package_contract():
    text = DOC.read_text(encoding="utf-8")

    required_terms = [
        ".cliany-adapter.tar.gz",
        'manifest_version: "1"',
        "schema_version: 3",
        "commands.py",
        "metadata.json",
        "manifest.json",
        "file_hashes",
        "cliany-site market publish",
        "cliany-site market install",
        "cliany-site market rollback",
    ]
    for term in required_terms:
        assert term in text


def test_adapter_lifecycle_referenced_paths_exist():
    paths = [
        "src/cliany_site/marketplace.py",
        "src/cliany_site/commands/market.py",
        "src/cliany_site/metadata.py",
        "src/cliany_site/codegen/generator.py",
        "tests/test_marketplace.py",
        "docs/contributor-starter.md",
        "cases/manifest.json",
        "docs/walkthroughs",
    ]
    for path in paths:
        assert (ROOT / path).exists(), f"missing referenced path: {path}"
