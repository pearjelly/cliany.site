import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "quickstart-10min.md"


def test_quickstart_documents_the_release_agnostic_first_success_path():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "pip install cliany-site",
        "cliany-site doctor",
        "cliany-site cases",
        "capabilities",
        "recommended_next_step",
        "ready_for_existing_adapters",
        "ready_for_demo_adapters",
        "case_catalog_quickstart",
        "demo_adapter_quickstart",
        "recommended_commands",
        "adapter_present",
        "安装目标已占用",
        "available=true",
        "deprecated=false",
        "verify",
        "verify --strict",
        "commands.py",
        "非零退出",
        "active",
        "candidate",
        "deprecated",
        "replacement",
        "下一步",
        "Real Demo Case Proposal",
        "cases/manifest.json",
        "cases/examples/",
        "python scripts/validate_cases.py --strict",
        "contributor-starter.md",
        "普通 `cliany-site doctor` 不会输出 `data.summary` 字段",
        "运行 `explore` 前仍先执行 live preflight",
        "未就绪时以非零结果停止，修复后重跑同一命令，不要继续 explore",
        "cliany-site doctor --json",
    ]
    for snippet in required:
        assert snippet in text

    assert "v0.14" not in text
    assert not re.search(r"\.cliany-adapter-v\d+(?:\.\d+)*(?:\.(?:tar\.gz|zip))?", text)
