from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cliany_site.explorer.engine import WorkflowExplorer, load_existing_adapter_context


class TestLoadExistingAdapterContext:
    def test_loads_commands_successfully(self, tmp_path: Path):
        adapter_dir = tmp_path / ".cliany-site" / "adapters" / "github.com"
        adapter_dir.mkdir(parents=True)
        metadata = {
            "domain": "github.com",
            "commands": [
                {
                    "name": "search",
                    "description": "搜索仓库",
                    "args": [
                        {"name": "query", "description": "搜索关键词"},
                    ],
                },
                {
                    "name": "login",
                    "description": "登录操作",
                    "args": [],
                },
            ],
        }
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            context = load_existing_adapter_context("github.com")

        assert context["domain"] == "github.com"
        assert len(context["existing_commands"]) == 2
        assert context["existing_commands"][0]["name"] == "search"
        assert context["existing_commands"][0]["description"] == "搜索仓库"
        assert len(context["existing_commands"][0]["args"]) == 1
        assert context["existing_commands"][0]["args"][0]["name"] == "query"
        assert context["existing_commands"][1]["name"] == "login"
        assert context["existing_commands"][1]["args"] == []

    def test_raises_file_not_found_when_domain_missing(self, tmp_path: Path):
        with patch("pathlib.Path.home", return_value=tmp_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_existing_adapter_context("nonexistent.com")

        assert "nonexistent.com" in str(exc_info.value)

    def test_returns_empty_commands_when_metadata_has_no_commands(self, tmp_path: Path):
        adapter_dir = tmp_path / ".cliany-site" / "adapters" / "empty.com"
        adapter_dir.mkdir(parents=True)
        metadata = {"domain": "empty.com", "commands": []}
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            context = load_existing_adapter_context("empty.com")

        assert context["domain"] == "empty.com"
        assert context["existing_commands"] == []

    def test_skips_non_dict_commands(self, tmp_path: Path):
        adapter_dir = tmp_path / ".cliany-site" / "adapters" / "bad.com"
        adapter_dir.mkdir(parents=True)
        metadata = {
            "domain": "bad.com",
            "commands": ["string_command", 42, {"name": "valid", "description": "ok", "args": []}],
        }
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            context = load_existing_adapter_context("bad.com")

        assert len(context["existing_commands"]) == 1
        assert context["existing_commands"][0]["name"] == "valid"

    def test_args_without_description_still_included(self, tmp_path: Path):
        adapter_dir = tmp_path / ".cliany-site" / "adapters" / "partial.com"
        adapter_dir.mkdir(parents=True)
        metadata = {
            "domain": "partial.com",
            "commands": [
                {
                    "name": "cmd",
                    "description": "测试命令",
                    "args": [{"name": "arg1"}],
                }
            ],
        }
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            context = load_existing_adapter_context("partial.com")

        assert context["existing_commands"][0]["args"][0]["name"] == "arg1"
        assert context["existing_commands"][0]["args"][0]["description"] == ""


class TestWorkflowExplorerExtendDomain:
    def test_extend_context_set_when_valid_domain(self, tmp_path: Path):
        adapter_dir = tmp_path / ".cliany-site" / "adapters" / "github.com"
        adapter_dir.mkdir(parents=True)
        metadata = {
            "domain": "github.com",
            "commands": [{"name": "search", "description": "搜索", "args": []}],
        }
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            explorer = WorkflowExplorer(extend_domain="github.com")

        assert explorer._extend_context is not None
        assert explorer._extend_context["domain"] == "github.com"
        assert len(explorer._extend_context["existing_commands"]) == 1

    def test_raises_file_not_found_when_extend_domain_missing(self, tmp_path: Path):
        with patch("pathlib.Path.home", return_value=tmp_path):
            with pytest.raises(FileNotFoundError):
                WorkflowExplorer(extend_domain="notexist.com")

    def test_extend_context_none_when_no_extend_domain(self):
        explorer = WorkflowExplorer()
        assert explorer._extend_context is None

    def test_explore_prompt_contains_existing_commands(self, tmp_path: Path):
        adapter_dir = tmp_path / ".cliany-site" / "adapters" / "example.com"
        adapter_dir.mkdir(parents=True)
        metadata = {
            "domain": "example.com",
            "commands": [
                {
                    "name": "search",
                    "description": "搜索功能",
                    "args": [{"name": "query", "description": "查询词"}],
                }
            ],
        }
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        captured_prompts: list = []

        async def fake_invoke(prompt):
            captured_prompts.append(prompt)
            mock_resp = MagicMock()
            mock_resp.content = json.dumps(
                {
                    "done": True,
                    "actions": [],
                    "commands": [
                        {
                            "name": "new-cmd",
                            "description": "新命令",
                            "args": [],
                            "action_steps": [],
                        }
                    ],
                    "reasoning": "测试",
                }
            )
            return mock_resp

        mock_llm = MagicMock()
        mock_llm.ainvoke = fake_invoke

        mock_tree = {
            "url": "https://example.com",
            "title": "Example",
            "selector_map": {},
            "screenshot": b"",
        }

        mock_browser_session = AsyncMock()
        mock_cdp = AsyncMock()
        mock_cdp.check_available = AsyncMock(return_value=True)
        mock_cdp.connect = AsyncMock(return_value=mock_browser_session)

        with (
            patch("pathlib.Path.home", return_value=tmp_path),
            patch("cliany_site.explorer.engine._get_llm", return_value=mock_llm),
            patch("cliany_site.explorer.engine.CDPConnection", return_value=mock_cdp),
            patch("cliany_site.explorer.engine.capture_axtree", AsyncMock(return_value=mock_tree)),
            patch("cliany_site.explorer.engine.serialize_axtree", return_value=""),
            patch(
                "cliany_site.explorer.engine.format_selector_candidates_section",
                return_value="",
            ),
            patch("cliany_site.explorer.engine.execute_action_steps", AsyncMock()),
            patch("cliany_site.explorer.engine.build_atom_inventory_section", return_value=""),
            patch("cliany_site.explorer.engine.save_extract_markdown", return_value=None),
            patch("cliany_site.explorer.engine.get_config") as mock_cfg,
        ):
            cfg = MagicMock()
            cfg.cdp_port = 9222
            cfg.explore_max_steps = 1
            cfg.vision_enabled = False
            cfg.llm_retry_max_attempts = 1
            cfg.llm_retry_base_delay = 1.0
            cfg.llm_retry_backoff_factor = 2.0
            mock_cfg.return_value = cfg

            explorer = WorkflowExplorer(extend_domain="example.com")

            asyncio.run(explorer.explore("https://example.com", "测试工作流", record=False))

        assert len(captured_prompts) >= 1
        prompt_text = captured_prompts[0]
        assert "search" in prompt_text
        assert "搜索功能" in prompt_text
        assert "已有命令" in prompt_text
        assert "请勿重复生成" in prompt_text
