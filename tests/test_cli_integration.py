"""L3 CLI 集成测试 — 验证所有命令注册、帮助文本、参数校验、错误降级。

使用 Click CliRunner，无需 Chrome/LLM 等外部依赖。
"""

import json
from importlib.metadata import version

from click.testing import CliRunner

from cliany_site.cli import cli


class TestRootCommand:
    """根命令基础功能"""

    def test_version_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert version("cliany-site") in result.output

    def test_help_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "cliany-site" in result.output

    def test_help_lists_all_builtin_commands(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        expected_commands = [
            "doctor",
            "login",
            "explore",
            "list",
            "tui",
            "check",
            "market",
            "workflow",
            "serve",
            "report",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"命令 '{cmd}' 未在 --help 输出中找到"

    def test_no_subcommand_shows_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Commands:" in result.output or "命令" in result.output

    def test_unknown_command_exits_nonzero(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["nonexistent-command-xyz"])
        assert result.exit_code != 0

    def test_global_options_parsed(self):
        """全局选项 --verbose/--debug/--sandbox 不应导致崩溃"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0
        result = runner.invoke(cli, ["--sandbox", "--help"])
        assert result.exit_code == 0


class TestBuiltinCommandHelp:
    """每个内置命令的 --help 应正常返回"""

    def _run_help(self, args: list[str]):
        runner = CliRunner()
        result = runner.invoke(cli, [*args, "--help"])
        assert result.exit_code == 0, f"'{' '.join(args)} --help' 退出码 {result.exit_code}: {result.output}"
        return result

    def test_doctor_help(self):
        result = self._run_help(["doctor"])
        assert "检查运行环境" in result.output or "CDP" in result.output

    def test_login_help(self):
        result = self._run_help(["login"])
        assert "Session" in result.output or "URL" in result.output.upper()

    def test_explore_help(self):
        result = self._run_help(["explore"])
        assert "探索" in result.output or "workflow" in result.output.lower()

    def test_list_help(self):
        result = self._run_help(["list"])
        assert "adapter" in result.output.lower() or "适配器" in result.output

    def test_check_help(self):
        result = self._run_help(["check"])
        assert "健康" in result.output or "AXTree" in result.output

    def test_tui_help(self):
        result = self._run_help(["tui"])
        assert "管理" in result.output or "界面" in result.output or "TUI" in result.output.upper()

    def test_serve_help(self):
        result = self._run_help(["serve"])
        assert "HTTP" in result.output or "API" in result.output or "port" in result.output

    def test_market_help(self):
        result = self._run_help(["market"])
        assert "适配器" in result.output or "market" in result.output.lower()

    def test_market_subcommands(self):
        """market 应包含 publish/install/uninstall/info/rollback/backups 子命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ["market", "--help"])
        assert result.exit_code == 0
        for subcmd in ["publish", "install", "uninstall", "info", "rollback", "backups"]:
            assert subcmd in result.output, f"market 缺少子命令 '{subcmd}'"

    def test_workflow_help(self):
        result = self._run_help(["workflow"])
        assert "工作流" in result.output or "workflow" in result.output.lower()

    def test_workflow_subcommands(self):
        """workflow 应包含 run/validate/batch 子命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "--help"])
        assert result.exit_code == 0
        for subcmd in ["run", "validate", "batch"]:
            assert subcmd in result.output, f"workflow 缺少子命令 '{subcmd}'"

    def test_report_help(self):
        result = self._run_help(["report"])
        assert "报告" in result.output or "report" in result.output.lower()

    def test_report_subcommands(self):
        """report 应包含 list/show 子命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "--help"])
        assert result.exit_code == 0
        for subcmd in ["list", "show"]:
            assert subcmd in result.output, f"report 缺少子命令 '{subcmd}'"


class TestParameterValidation:
    """命令缺少必要参数时应优雅报错"""

    def test_explore_missing_args(self):
        """explore 缺少 URL 和 workflow 参数"""
        runner = CliRunner()
        result = runner.invoke(cli, ["explore"])
        assert result.exit_code != 0

    def test_login_missing_url(self):
        """login 缺少 URL 参数"""
        runner = CliRunner()
        result = runner.invoke(cli, ["login"])
        assert result.exit_code != 0

    def test_check_missing_domain(self):
        """check 缺少 domain 参数"""
        runner = CliRunner()
        result = runner.invoke(cli, ["check"])
        assert result.exit_code != 0

    def test_market_publish_missing_domain(self):
        """market publish 缺少 domain"""
        runner = CliRunner()
        result = runner.invoke(cli, ["market", "publish"])
        assert result.exit_code != 0

    def test_market_install_missing_path(self):
        """market install 缺少 pack_path"""
        runner = CliRunner()
        result = runner.invoke(cli, ["market", "install"])
        assert result.exit_code != 0

    def test_workflow_run_missing_file(self):
        """workflow run 缺少 YAML 文件"""
        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "run"])
        assert result.exit_code != 0

    def test_workflow_batch_missing_args(self):
        """workflow batch 缺少 adapter/command/data_file"""
        runner = CliRunner()
        result = runner.invoke(cli, ["workflow", "batch"])
        assert result.exit_code != 0

    def test_report_show_missing_id(self):
        """report show 缺少 report_id"""
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "show"])
        assert result.exit_code != 0


class TestRootJsonErrorEnvelope:
    """根 CLI --json 模式下错误应使用新 envelope 格式 {ok: false}，不得使用旧 {success: false}"""

    def test_invalid_option_uses_new_envelope(self):
        """无效选项（UsageError）应返回 {ok: false, error.code, error.message}"""
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--invalid-option-xyz", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert "ok" in data, "新信封必须有 ok 字段"
        assert data["ok"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "success" not in data, "不得出现旧信封 success 字段"

    def test_unknown_command_uses_new_envelope(self):
        """未知命令（UsageError）应返回 ok=false 且 error.code == E_INVALID_PARAM"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "nonexistent-command-xyz"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "E_INVALID_PARAM"
        assert "success" not in data

    def test_unloadable_adapter_uses_static_verification_error(self, tmp_home, no_llm):
        """存在但无法注册的 adapter 必须返回可执行的静态校验提示。"""
        from cliany_site.config import get_config
        from cliany_site.loader import register_adapters

        domain = "not-a-group.local"
        adapter_dir = get_config().adapters_dir / domain
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "metadata.json").write_text(
            json.dumps({"schema_version": 3, "domain": domain, "commands": []}),
            encoding="utf-8",
        )
        (adapter_dir / "commands.py").write_text(
            "import click\n\ncli = click.Command('not-a-group')\n",
            encoding="utf-8",
        )

        previous_errors = dict(getattr(cli, "_adapter_load_errors", {}))
        try:
            registration = register_adapters(cli)
            cli.set_adapter_load_errors(registration["adapter_load_errors"])

            runner = CliRunner()
            json_result = runner.invoke(cli, ["--json", domain, "search"])
            assert json_result.exit_code == 1
            data = json.loads(json_result.output)
            assert data["ok"] is False
            assert data["error"]["code"] == "E_VERIFY_STATIC"
            assert data["error"]["details"] == {
                "domain": domain,
                "verdict": "commands_unloadable",
                "reason": "commands.py 必须导出 click.Group 类型的 cli",
            }
            assert data["error"]["hint"] == (
                f"运行 cliany-site verify {domain} --strict --json 查看并修复静态校验失败。"
            )

            human_result = runner.invoke(cli, [domain, "search"])
            assert human_result.exit_code == 1
            assert "E_VERIFY_STATIC" in human_result.output
            assert f"verify {domain} --strict --json" in human_result.output
        finally:
            cli.set_adapter_load_errors(previous_errors)

    def test_adapter_missing_commands_uses_static_verification_error(self, tmp_home, no_llm):
        """存在 metadata 但缺失 commands.py 的 adapter 必须保留 commands_missing verdict。"""
        from cliany_site.config import get_config
        from cliany_site.loader import register_adapters

        domain = "missing-commands.local"
        adapter_dir = get_config().adapters_dir / domain
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "metadata.json").write_text(
            json.dumps({"schema_version": 3, "domain": domain, "commands": []}),
            encoding="utf-8",
        )

        previous_errors = dict(getattr(cli, "_adapter_load_errors", {}))
        try:
            registration = register_adapters(cli)
            cli.set_adapter_load_errors(registration["adapter_load_errors"])

            result = CliRunner().invoke(cli, ["--json", domain, "search"])
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["error"]["code"] == "E_VERIFY_STATIC"
            assert data["error"]["details"] == {
                "domain": domain,
                "verdict": "commands_missing",
                "reason": "commands.py 不存在",
            }
        finally:
            cli.set_adapter_load_errors(previous_errors)

    def test_symlinked_commands_uses_static_verification_error_before_importing(self, tmp_home, no_llm):
        """根 CLI 不得沿符号链接导入 adapter 代码。"""
        from cliany_site.config import get_config
        from cliany_site.loader import register_adapters

        domain = "linked-commands.local"
        adapter_dir = get_config().adapters_dir / domain
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "metadata.json").write_text(
            json.dumps({"schema_version": 3, "domain": domain, "commands": []}),
            encoding="utf-8",
        )
        imported_marker = tmp_home / "commands-imported"
        outside_commands = tmp_home / "outside-commands.py"
        outside_commands.write_text(
            "from pathlib import Path\n"
            f"Path({str(imported_marker)!r}).write_text('imported')\n"
            "import click\n\n@click.group()\ndef cli():\n    pass\n",
            encoding="utf-8",
        )
        (adapter_dir / "commands.py").symlink_to(outside_commands)

        previous_errors = dict(getattr(cli, "_adapter_load_errors", {}))
        try:
            registration = register_adapters(cli)
            cli.set_adapter_load_errors(registration["adapter_load_errors"])

            result = CliRunner().invoke(cli, ["--json", domain, "search"])

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["error"]["code"] == "E_VERIFY_STATIC"
            assert data["error"]["details"] == {
                "domain": domain,
                "verdict": "security_issue",
                "reason": "commands.py 不能是符号链接",
            }
            assert not imported_marker.exists()
        finally:
            cli.set_adapter_load_errors(previous_errors)

    def test_symlinked_manifest_uses_static_verification_error_before_importing(self, tmp_home, no_llm):
        """根 CLI 不得在 manifest 路径离开 adapter 目录后导入命令。"""
        from cliany_site.config import get_config
        from cliany_site.loader import register_adapters

        domain = "linked-manifest.local"
        adapter_dir = get_config().adapters_dir / domain
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "metadata.json").write_text(
            json.dumps({"schema_version": 3, "domain": domain, "commands": []}),
            encoding="utf-8",
        )
        imported_marker = tmp_home / "commands-imported"
        (adapter_dir / "commands.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(imported_marker)!r}).write_text('imported')\n"
            "import click\n\n@click.group()\ndef cli():\n    pass\n",
            encoding="utf-8",
        )
        outside_manifest = tmp_home / "outside-manifest.json"
        outside_manifest.write_text("{}", encoding="utf-8")
        (adapter_dir / "manifest.json").symlink_to(outside_manifest)

        previous_errors = dict(getattr(cli, "_adapter_load_errors", {}))
        try:
            registration = register_adapters(cli)
            cli.set_adapter_load_errors(registration["adapter_load_errors"])

            result = CliRunner().invoke(cli, ["--json", domain, "search"])

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["error"]["code"] == "E_VERIFY_STATIC"
            assert data["error"]["details"] == {
                "domain": domain,
                "verdict": "security_issue",
                "reason": "manifest.json 不能是符号链接",
            }
            assert not imported_marker.exists()
        finally:
            cli.set_adapter_load_errors(previous_errors)

    def test_schema_rejected_adapter_uses_static_verification_error(self, tmp_home, no_llm):
        """非对象 metadata 不得阻断 CLI 启动，且必须返回可定位的静态错误。"""
        from cliany_site.config import get_config
        from cliany_site.loader import register_adapters

        domain = "bad-metadata.local"
        adapter_dir = get_config().adapters_dir / domain
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "metadata.json").write_text("[]", encoding="utf-8")
        (adapter_dir / "commands.py").write_text(
            "import click\n\n@click.group()\ndef cli():\n    pass\n",
            encoding="utf-8",
        )

        previous_errors = dict(getattr(cli, "_adapter_load_errors", {}))
        try:
            registration = register_adapters(cli)
            cli.set_adapter_load_errors(registration["adapter_load_errors"])

            result = CliRunner().invoke(cli, ["--json", domain, "search"])
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["error"]["code"] == "E_VERIFY_STATIC"
            assert data["error"]["details"] == {
                "domain": domain,
                "verdict": "schema_error",
                "reason": "metadata.json 必须是 JSON object",
            }
        finally:
            cli.set_adapter_load_errors(previous_errors)

    def test_invalid_option_error_code_is_e_invalid_param(self):
        """UsageError 的 code 必须是 E_INVALID_PARAM"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "list", "--no-such-flag"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "E_INVALID_PARAM"


class TestListLegacyFiltering:
    """list --json 默认应隐藏 legacy adapter；--legacy --json 才显示"""

    def test_list_json_hides_legacy_by_default(self, tmp_home, no_llm):
        """list --json 不应返回 loader 会跳过的 legacy adapter"""
        adapters_dir = tmp_home / ".cliany-site" / "adapters"
        legacy_dir = adapters_dir / "old.local"
        legacy_dir.mkdir(parents=True)
        import json as _json
        (legacy_dir / "metadata.json").write_text(
            _json.dumps({"domain": "old.local", "schema_version": "1", "commands": []}),
            encoding="utf-8",
        )
        (legacy_dir / "commands.py").write_text(
            "import click\n\n@click.group()\ndef cli():\n    pass\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json"])
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        domains = [a["domain"] for a in data["data"]["adapters"]]
        assert "old.local" not in domains, "legacy adapter 不应出现在默认 list 中"

    def test_list_legacy_flag_shows_legacy(self, tmp_home, no_llm):
        """list --legacy --json 应能看到 legacy adapter"""
        adapters_dir = tmp_home / ".cliany-site" / "adapters"
        legacy_dir = adapters_dir / "old.local"
        legacy_dir.mkdir(parents=True)
        import json as _json
        (legacy_dir / "metadata.json").write_text(
            _json.dumps({"domain": "old.local", "schema_version": "1", "commands": []}),
            encoding="utf-8",
        )
        (legacy_dir / "commands.py").write_text(
            "import click\n\n@click.group()\ndef cli():\n    pass\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--legacy", "--json"])
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        domains = [item["domain"] for item in data["data"]]
        assert "old.local" in domains, "legacy adapter 应出现在 --legacy 列表中"


class TestJsonOutput:
    """--json 模式下的输出格式验证"""

    def test_list_json_output(self):
        """list --json 应返回有效 JSON 信封"""
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "ok" in data
        assert "data" in data
        assert "error" in data
        assert data["ok"] is True

    def test_report_list_json_output(self):
        """report list --json 应返回有效 JSON 信封"""
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "reports" in data["data"]

    def test_json_error_envelope(self):
        """JSON 模式下错误输出应包含 error.code 和 error.message"""
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "show", "nonexistent-report-id-xyz", "--json"])
        try:
            data = json.loads(result.output)
            if not data.get("success"):
                assert "code" in data["error"]
                assert "message" in data["error"]
        except json.JSONDecodeError:
            pass

    def test_global_json_flag_propagates(self):
        """根级 --json 应传递到子命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--json", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
