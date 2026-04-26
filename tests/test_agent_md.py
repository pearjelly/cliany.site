from __future__ import annotations

import pytest

from cliany_site.agent_md import (
    SENTINEL_END,
    SENTINEL_START,
    AgentMdResult,
    _compute_hash,
    _render_section,
    regenerate,
)
from cliany_site.registry import Registry


@pytest.fixture
def empty_registry():
    return Registry()


@pytest.fixture
def simple_registry():
    r = Registry()
    r.collect(["doctor", "login"], [], [])
    return r


def test_first_write_creates_sentinel(tmp_path, empty_registry):
    result = regenerate(tmp_path, empty_registry)

    assert isinstance(result, AgentMdResult)
    assert result.written is True
    assert result.conflict is False
    assert result.version == 1

    agent_md = tmp_path / "AGENT.md"
    assert agent_md.exists()
    content = agent_md.read_text()
    assert "<!-- cliany-site:auto-generated v=" in content
    assert SENTINEL_END in content


def test_idempotent_second_write(tmp_path, empty_registry):
    result1 = regenerate(tmp_path, empty_registry)
    assert result1.written is True

    result2 = regenerate(tmp_path, empty_registry)
    assert result2.written is True
    assert result2.conflict is False

    content = (tmp_path / "AGENT.md").read_text()
    assert content.count("<!-- cliany-site:auto-generated") == 1
    assert content.count(SENTINEL_END) == 1


def test_user_section_preserved(tmp_path, empty_registry):
    agent_md = tmp_path / "AGENT.md"
    regenerate(tmp_path, empty_registry)

    existing = agent_md.read_text()
    agent_md.write_text(existing + "\n## My Notes\nkeep me\n")

    result = regenerate(tmp_path, empty_registry)
    assert result.written is True
    assert result.conflict is False

    content = agent_md.read_text()
    assert "keep me" in content
    assert "<!-- cliany-site:auto-generated" in content
    assert SENTINEL_END in content


def test_conflict_detection(tmp_path, empty_registry):
    regenerate(tmp_path, empty_registry)

    agent_md = tmp_path / "AGENT.md"
    content = agent_md.read_text()

    sentinel_start_prefix = "<!-- cliany-site:auto-generated"
    start_pos = content.find(sentinel_start_prefix)
    first_newline = content.index("\n", start_pos)
    end_pos = content.find(SENTINEL_END)

    modified = (
        content[: first_newline + 1]
        + "## 手动修改的内容\n某人改了这里\n"
        + content[end_pos:]
    )
    agent_md.write_text(modified)

    result = regenerate(tmp_path, empty_registry, force=False)
    assert result.conflict is True
    assert result.written is False


def test_force_overrides_conflict(tmp_path, empty_registry):
    regenerate(tmp_path, empty_registry)

    agent_md = tmp_path / "AGENT.md"
    content = agent_md.read_text()

    sentinel_start_prefix = "<!-- cliany-site:auto-generated"
    start_pos = content.find(sentinel_start_prefix)
    first_newline = content.index("\n", start_pos)
    end_pos = content.find(SENTINEL_END)

    modified = (
        content[: first_newline + 1]
        + "## 手动修改的内容\n某人改了这里\n"
        + content[end_pos:]
    )
    agent_md.write_text(modified)

    result = regenerate(tmp_path, empty_registry, force=True)
    assert result.written is True
    assert result.conflict is False

    new_content = agent_md.read_text()
    assert "手动修改的内容" not in new_content
    assert "某人改了这里" not in new_content


def test_env_skip(tmp_path, empty_registry):
    result = regenerate(tmp_path, empty_registry, env_skip=True)
    assert result.written is False
    assert result.conflict is False
    assert not (tmp_path / "AGENT.md").exists()


def test_registry_commands_appear_in_table(tmp_path, simple_registry):
    regenerate(tmp_path, simple_registry)
    content = (tmp_path / "AGENT.md").read_text()
    assert "| `doctor`" in content
    assert "| `login`" in content


def test_compute_hash_length():
    h = _compute_hash("some content")
    assert len(h) == 16
    assert h.isalnum()


def test_render_section_table_structure(empty_registry):
    section = _render_section(empty_registry, version=1)
    assert "## cliany-site 命令清单（自动生成）" in section
    assert "| 命令 | 说明 |" in section
    assert "|------|------|" in section


def test_sentinel_start_format_contains_hash_and_version():
    sentinel = SENTINEL_START.format(v=2, h="deadbeef12345678")
    assert "v=2" in sentinel
    assert "hash=deadbeef12345678" in sentinel


def test_existing_file_content_preserved_on_first_write(tmp_path, empty_registry):
    agent_md = tmp_path / "AGENT.md"
    agent_md.write_text("# 项目文档\n\n现有内容\n")

    result = regenerate(tmp_path, empty_registry)
    assert result.written is True

    content = agent_md.read_text()
    assert "# 项目文档" in content
    assert "现有内容" in content
    assert "<!-- cliany-site:auto-generated" in content
