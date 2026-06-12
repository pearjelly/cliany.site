from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "good-first-issues.md"


def _candidate_task_rows(text: str) -> list[list[str]]:
    lines = text.splitlines()
    header_index = lines.index("| Label | 任务 | 主要文件 | 验证 |")
    rows: list[list[str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def test_good_first_issues_doc_has_issue_drafting_checklist():
    text = DOC.read_text(encoding="utf-8")

    required = [
        "# Good First Issues",
        "## 候选任务",
        "## Issue 拆分清单",
        "## 维护者使用方式",
        "期望改动范围",
        "推荐验证命令",
        "相关文件链接",
        "验收证据",
        "明确非目标",
        "不需要真实 LLM key",
        "~/.cliany-site/",
    ]
    for snippet in required:
        assert snippet in text


def test_good_first_issue_candidates_keep_local_validation_commands():
    text = DOC.read_text(encoding="utf-8")
    rows = _candidate_task_rows(text)

    assert rows
    for label, task, files, validation in rows:
        assert label.startswith("`") and label.endswith("`")
        assert task
        assert "`" in files, f"missing concrete file path in row: {task}"
        assert validation
        assert any(
            command in validation
            for command in (
                "python ",
                "pytest ",
                "ruff check",
                "git diff --check",
                "CLIANY_QA_OFFLINE=1",
            )
        ), f"missing runnable validation command in row: {task}"


def test_good_first_issues_split_candidate_promotion_tasks():
    text = DOC.read_text(encoding="utf-8")
    rows = _candidate_task_rows(text)
    tasks = "\n".join(row[1] for row in rows)
    validations = "\n".join(row[3] for row in rows)

    for snippet in ("adapter_package", "metadata_validation", "online_smoke"):
        assert snippet in tasks
    assert "python scripts/validate_cases.py --json" in validations
    assert "pytest tests/test_validate_cases.py -q --no-cov" in validations
    assert "git diff --check" in validations
