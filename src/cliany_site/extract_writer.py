from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import click


def _sanitize_filename(description: str) -> str:
    name = description[:50]
    name = re.sub(r'[/\\:*?"<>|]', "", name)
    name = re.sub(r"[\s\u3000]+", "_", name)
    name = name.strip("_")
    if not name:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"extract_{ts}.md"
    if not name.endswith(".md"):
        name = name + ".md"
    return name


def _render_text(data) -> str:
    if data is None:
        return ""
    if isinstance(data, dict):
        return str(data.get("text", ""))
    return str(data)


def _render_attribute(data: dict) -> str:
    if not data or not isinstance(data, dict):
        return ""
    return "\n".join(f"- **{k}**: {v}" for k, v in data.items())


def _build_md_table(headers: list, rows: list) -> str:
    if not headers:
        return ""
    header_row = "| " + " | ".join(str(h) for h in headers) + " |"
    sep_row = "| " + " | ".join("---" for _ in headers) + " |"
    result_rows = [header_row, sep_row]
    for row in rows:
        padded = list(row) + [""] * (len(headers) - len(row))
        result_rows.append("| " + " | ".join(str(c) for c in padded[: len(headers)]) + " |")
    return "\n".join(result_rows)


def _dict_list_to_table(data: list) -> str:
    if not data:
        return ""
    headers: list[str] = []
    for item in data:
        if isinstance(item, dict):
            headers = list(item.keys())
            break
    if not headers:
        return ""
    rows = [[str(item.get(h, "")) for h in headers] for item in data if isinstance(item, dict)]
    return _build_md_table(headers, rows)


def _render_list(data: list) -> str:
    if not data or not isinstance(data, list):
        return ""
    first = next((item for item in data if item is not None), None)
    if first is None:
        return ""
    if isinstance(first, dict):
        return _dict_list_to_table(data)
    return "\n".join(f"- {item}" for item in data)


def _render_table(data: list) -> str:
    if not data or not isinstance(data, list):
        return ""
    first = next((item for item in data if item is not None), None)
    if first is None:
        return ""
    if isinstance(first, dict):
        return _dict_list_to_table(data)
    if isinstance(first, list):
        return _build_md_table(data[0], data[1:])
    return ""


def _format_markdown(
    extraction_results: list[dict],
    domain: str,
    workflow: str,
) -> str:
    ts = datetime.now(UTC).isoformat()
    count = len(extraction_results)
    lines = [
        "---",
        f"domain: {domain}",
        f'workflow: "{workflow}"',
        f"timestamp: {ts}",
        f"extract_count: {count}",
        "---",
        "",
    ]
    for i, result in enumerate(extraction_results, start=1):
        description = str(result.get("description", f"提取 {i}"))
        extract_mode = str(result.get("extract_mode", ""))
        data = result.get("data")

        lines.append(f"## 提取 {i}: {description}")
        lines.append("")

        if extract_mode == "text":
            content = _render_text(data)
        elif extract_mode == "attribute":
            content = _render_attribute(data) if isinstance(data, dict) else _render_text(data)
        elif extract_mode == "list":
            content = _render_list(data) if isinstance(data, list) else _render_text(data)
        elif extract_mode == "table":
            content = _render_table(data) if isinstance(data, list) else _render_text(data)
        else:
            try:
                content = "```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```"
            except Exception:
                content = str(data)

        if content:
            lines.append(content)
        lines.append("")

    return "\n".join(lines)


def save_extract_markdown(
    extraction_results: list[dict],
    domain: str,
    workflow_description: str,
    output_path: Path | None = None,
) -> str | None:
    """
    将 extraction_results 保存为 Markdown 文件。

    - extraction_results 为空或 None 时返回 None，不创建文件
    - 成功返回写入的文件路径字符串
    - 任何异常被捕获，stderr 输出警告，返回 None
    """
    try:
        if not extraction_results:
            return None

        content = _format_markdown(extraction_results, domain, workflow_description)

        if output_path is None:
            filename = _sanitize_filename(workflow_description)
            output_path = Path.home() / ".cliany-site" / "adapters" / domain / "extracts" / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        return str(output_path)

    except Exception as exc:
        click.echo(f"⚠️ extract 结果保存失败: {exc}", err=True)
        return None
