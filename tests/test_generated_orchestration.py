from __future__ import annotations

import json
import types

from click.testing import CliRunner

from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult

MINIMAL_CODE = (
    "# 自动生成 — DO NOT EDIT\n"
    "# 来源 URL: https://example.com\n"
    "# 工作流: test\n"
    "import click\n"
    "@click.group()\n"
    "def cli(): pass\n"
)


def _make_explore_result(
    actions: list[ActionStep] | None = None,
    commands: list[CommandSuggestion] | None = None,
) -> ExploreResult:
    return ExploreResult(
        actions=actions or [],
        commands=commands or [],
    )


def _simple_result() -> ExploreResult:
    actions = [
        ActionStep(action_type="navigate", page_url="https://example.com", target_url="https://example.com"),
        ActionStep(action_type="click", page_url="https://example.com", target_ref="ref-1", target_name="搜索按钮"),
    ]
    commands = [
        CommandSuggestion(name="search", description="搜索内容", args=[], action_steps=[0, 1]),
    ]
    return _make_explore_result(actions=actions, commands=commands)


class TestGeneratedNoCdpImport:

    def test_no_cdp_import_in_generated_code(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "from cliany_site.browser" not in code
        assert "cdp_from_context" not in code
        assert "CDPConnection" not in code

    def test_no_asyncio_run_wrapper_in_generated_code(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "asyncio.run(_run())" not in code

    def test_runtime_helpers_import_present(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "execute_steps_via_atoms" in code

    def test_execute_steps_via_atoms_called(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "execute_steps_via_atoms(action_steps, SOURCE_URL, DOMAIN)" in code

    def test_generated_json_payload_includes_quality_summary(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "summarize_extract_quality(results, action_steps)" in code
        assert '"quality": quality' in code

    def test_generated_list_command_fails_when_quality_is_empty(self):
        actions = [
            ActionStep(
                action_type="extract",
                page_url="https://example.com",
                selector=".result",
                extract_mode="list",
                fields_map={"title": "h3", "url": "a@href"},
            )
        ]
        commands = [
            CommandSuggestion(name="list-results", description="列出结果", args=[], action_steps=[0]),
        ]
        code = AdapterGenerator(domain="example.com").generate(
            _make_explore_result(actions=actions, commands=commands),
            "example.com",
        )

        assert 'if quality.get("status") == "empty":' in code
        assert '"code": "E_EMPTY_RESULT"' in code
        assert '"details": quality' in code

    def test_generated_list_command_returns_empty_result_error(self):
        actions = [
            ActionStep(
                action_type="extract",
                page_url="https://example.com",
                selector=".result",
                extract_mode="list",
                fields_map={"title": "h3", "url": "a@href"},
            )
        ]
        commands = [
            CommandSuggestion(name="list-results", description="列出结果", args=[], action_steps=[0]),
        ]
        code = AdapterGenerator(domain="example.com").generate(
            _make_explore_result(actions=actions, commands=commands),
            "example.com",
        )
        module = types.ModuleType("generated_adapter")
        exec(code, module.__dict__)  # noqa: S102 - 测试生成代码的 Click 行为
        quality = {
            "status": "empty",
            "ok": False,
            "extracts": [{"issues": ["all rows are blank"]}],
        }
        module.execute_steps_via_atoms = lambda action_steps, source_url, domain: [  # noqa: ARG005
            {"ok": True, "command": "browser extract", "data": {"content": [{"title": "", "url": ""}]}}
        ]
        module.summarize_extract_quality = lambda results, action_steps: quality  # noqa: ARG005

        result = CliRunner().invoke(module.cli, ["list-results", "--json"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert payload["error"]["code"] == "E_EMPTY_RESULT"
        assert payload["error"]["details"] == quality
        assert payload["data"]["quality"] == quality


class TestGeneratedCodeStructure:

    def test_generated_code_has_header(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "# 自动生成 — DO NOT EDIT" in code
        assert "DOMAIN = " in code
        assert "SOURCE_URL = " in code

    def test_generated_code_has_cli_group(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert "@click.group()" in code
        assert "def cli():" in code

    def test_generated_command_has_json_option(self):
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(_simple_result(), "example.com")
        assert '"--json"' in code or "--json" in code

    def test_empty_commands_generates_fallback(self):
        result = _make_explore_result(actions=[], commands=[])
        gen = AdapterGenerator(domain="example.com")
        code = gen.generate(result, "example.com")
        assert "def " in code
        assert "execute_steps_via_atoms" in code


class TestCanonicalActionsPopulated:

    def test_canonical_actions_populated_from_explore_result(self, tmp_home):
        actions = [
            ActionStep(action_type="navigate", page_url="https://example.com", target_url="https://example.com"),
            ActionStep(action_type="click", page_url="https://example.com", target_ref="ref-1", target_name="按钮"),
        ]
        result = _make_explore_result(actions=actions)
        save_adapter("example.com", MINIMAL_CODE, explore_result=result)
        meta_path = tmp_home / ".cliany-site" / "adapters" / "example.com" / "metadata.json"
        meta = json.loads(meta_path.read_text())
        assert len(meta["canonical_actions"]) == 2
        assert meta["canonical_actions"][0]["action_type"] == "navigate"
        assert meta["canonical_actions"][1]["action_type"] == "click"
        assert meta["canonical_actions"][1]["target_ref"] == "ref-1"

    def test_canonical_actions_empty_without_explore_result(self, tmp_home):
        save_adapter("example.com", MINIMAL_CODE)
        meta_path = tmp_home / ".cliany-site" / "adapters" / "example.com" / "metadata.json"
        meta = json.loads(meta_path.read_text())
        assert meta["canonical_actions"] == []

    def test_canonical_actions_skips_empty_action_type(self, tmp_home):
        actions = [
            ActionStep(action_type="navigate", page_url="https://example.com"),
            ActionStep(action_type="", page_url="https://example.com"),
        ]
        result = _make_explore_result(actions=actions)
        save_adapter("example.com", MINIMAL_CODE, explore_result=result)
        meta_path = tmp_home / ".cliany-site" / "adapters" / "example.com" / "metadata.json"
        meta = json.loads(meta_path.read_text())
        assert len(meta["canonical_actions"]) == 1
        assert meta["canonical_actions"][0]["action_type"] == "navigate"
