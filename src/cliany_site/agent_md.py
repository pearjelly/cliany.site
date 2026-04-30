"""AGENT.md 自动渲染与幂等更新"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

SENTINEL_START = "<!-- cliany-site:auto-generated v={v} hash={h} -->"
SENTINEL_END = "<!-- end cliany-site:auto-generated -->"
_SENTINEL_RE = re.compile(
    r"<!-- cliany-site:auto-generated v=(\d+) hash=([a-f0-9]+) -->.*?"
    r"<!-- end cliany-site:auto-generated -->",
    re.DOTALL,
)


@dataclass
class AgentMdResult:
    written: bool
    conflict: bool
    path: Path
    version: int


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _render_section(registry: object, version: int) -> str:  # noqa: ARG001
    lines = [
        "## cliany-site 命令清单（自动生成）",
        "",
        "| 命令 | 说明 |",
        "|------|------|",
    ]
    try:
        for entry in registry.list():  # type: ignore[attr-defined]
            desc = getattr(entry, "description", "") or ""
            lines.append(f"| `{entry.name}` | {desc} |")
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(lines)


def regenerate(
    project_root: Path,
    registry: object,
    version: int = 1,
    force: bool = False,
    env_skip: bool = False,
) -> AgentMdResult:
    """
    幂等写 project_root/AGENT.md 的自动生成段。

    - 首次：写 sentinel + 内容
    - 二次：sentinel 段刷新，sentinel 外内容保留
    - 手动修改后：冲突检测（hash 不匹配），force=False 时返回 conflict=True 不写入
    - env_skip（CLIANY_NO_AGENT_MD=1）：直接返回 written=False
    """
    agent_md_path = project_root / "AGENT.md"

    if env_skip:
        return AgentMdResult(
            written=False, conflict=False, path=agent_md_path, version=version
        )

    section_content = _render_section(registry, version)
    content_hash = _compute_hash(section_content)
    sentinel_start_line = SENTINEL_START.format(v=version, h=content_hash)
    new_block = f"{sentinel_start_line}\n{section_content}\n{SENTINEL_END}"

    existing_text = ""
    if agent_md_path.exists():
        existing_text = agent_md_path.read_text(encoding="utf-8")

    match = _SENTINEL_RE.search(existing_text)

    if match is None:
        if existing_text:
            sep = "\n" if existing_text.endswith("\n") else "\n\n"
            new_text = existing_text + sep + new_block + "\n"
        else:
            new_text = new_block + "\n"
        agent_md_path.write_text(new_text, encoding="utf-8")
        return AgentMdResult(
            written=True, conflict=False, path=agent_md_path, version=version
        )

    stored_hash = match.group(2)
    full_block = match.group(0)

    # 提取 sentinel 块内部内容（去掉首行 sentinel_start 和末行 sentinel_end）
    newline_pos = full_block.index("\n")
    inner_and_end = full_block[newline_pos + 1 :]
    end_pos = inner_and_end.rfind(SENTINEL_END)
    inner_content = inner_and_end[:end_pos].rstrip("\n")

    # 计算当前内部内容的 hash，与 sentinel 记录的 hash 对比
    actual_hash = _compute_hash(inner_content)

    if actual_hash != stored_hash and not force:
        return AgentMdResult(
            written=False, conflict=True, path=agent_md_path, version=version
        )

    # 替换 sentinel 块（保留 sentinel 之外的用户内容）
    new_text = existing_text[: match.start()] + new_block + existing_text[match.end() :]
    agent_md_path.write_text(new_text, encoding="utf-8")
    return AgentMdResult(
        written=True, conflict=False, path=agent_md_path, version=version
    )
