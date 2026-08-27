"""Python SDK + HTTP API 服务测试"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_config(tmp_path: Path) -> MagicMock:
    cfg = MagicMock()
    cfg.home_dir = tmp_path
    cfg.adapters_dir = tmp_path / "adapters"
    cfg.sessions_dir = tmp_path / "sessions"
    cfg.reports_dir = tmp_path / "reports"
    cfg.logs_dir = tmp_path / "logs"
    cfg.activity_log_path = tmp_path / "activity.log"
    cfg.cdp_port = 9222
    cfg.browser_provider = ""  # 默认空字符串表示 Chrome
    cfg.adapters_dir.mkdir(parents=True, exist_ok=True)
    cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
    cfg.to_dict.return_value = {"cdp_port": 9222, "home_dir": str(tmp_path)}
    return cfg


def _create_adapter_with_actions(tmp_path: Path, domain: str = "test.com") -> Path:
    cfg_mock = _make_config(tmp_path)
    adapter_dir = cfg_mock.adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)

    commands_py = adapter_dir / "commands.py"
    commands_py.write_text(
        "import click\n\n@click.group()\ndef cli():\n    pass\n",
        encoding="utf-8",
    )

    metadata = {
        "schema_version": 3,
        "domain": domain,
        "generated_at": "2026-01-01T00:00:00Z",
        "generator_version": "0.9.0",
        "commands": [{"name": "search"}],
        "command_defs": [
            {
                "name": "search",
                "description": "搜索",
                "actions": [
                    {"type": "navigate", "url": f"https://{domain}/search"},
                    {"type": "type", "ref": "1", "value": "test", "description": "输入搜索词"},
                ],
            }
        ],
    }
    metadata_path = adapter_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    return adapter_dir


def _write_manifest(adapter_dir: Path, domain: str, extra_files: dict[str, Path] | None = None) -> None:
    files = ["commands.py", "metadata.json"]
    file_hashes = {
        filename: hashlib.sha256((adapter_dir / filename).read_bytes()).hexdigest()
        for filename in files
    }
    for filename, source_path in (extra_files or {}).items():
        files.append(filename)
        file_hashes[filename] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    (adapter_dir / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "1",
                "domain": domain,
                "version": "1.0.0",
                "files": files,
                "file_hashes": file_hashes,
            }
        ),
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════
# SDK — ClanySite 异步上下文管理器
# ═══════════════════════════════════════════════════════════


class TestClanySiteContextManager:
    @pytest.mark.asyncio
    async def test_enter_exit(self):
        from cliany_site.sdk import ClanySite

        async with ClanySite() as cs:
            assert cs is not None
            assert cs._cdp is None
            assert cs._session is None

    @pytest.mark.asyncio
    async def test_close_without_connection(self):
        from cliany_site.sdk import ClanySite

        cs = ClanySite()
        await cs.close()

    @pytest.mark.asyncio
    async def test_close_disconnects_cdp(self):
        from cliany_site.sdk import ClanySite

        cs = ClanySite()
        mock_cdp = AsyncMock()
        cs._cdp = mock_cdp
        await cs.close()
        mock_cdp.disconnect.assert_awaited_once()
        assert cs._cdp is None

    @pytest.mark.asyncio
    async def test_ensure_cdp_creates_connection(self):
        from cliany_site.sdk import ClanySite

        cs = ClanySite(cdp_url="http://remote:9222")
        with patch("cliany_site.sdk.ClanySite._ensure_cdp") as mock:
            mock_cdp = AsyncMock()
            mock.return_value = mock_cdp
            result = await cs._ensure_cdp()
            assert result is mock_cdp

    @pytest.mark.asyncio
    async def test_ensure_browser_session_raises_on_unavailable(self):
        from cliany_site.errors import CdpError
        from cliany_site.sdk import ClanySite

        cs = ClanySite()
        mock_cdp = AsyncMock()
        mock_cdp.check_available = AsyncMock(return_value=False)
        cs._cdp = mock_cdp

        with pytest.raises(CdpError, match="CDP 不可用"):
            await cs._ensure_browser_session()


class TestClanySiteInit:
    def test_default_params(self):
        from cliany_site.sdk import ClanySite

        cs = ClanySite()
        assert cs._cdp_url is None
        assert cs._headless is None
        assert cs._port is None

    def test_custom_params(self):
        from cliany_site.sdk import ClanySite

        cs = ClanySite(cdp_url="ws://host:9222", headless=True, port=9333)
        assert cs._cdp_url == "ws://host:9222"
        assert cs._headless is True
        assert cs._port == 9333


# ═══════════════════════════════════════════════════════════
# SDK — doctor
# ═══════════════════════════════════════════════════════════


class TestSDKDoctor:
    @pytest.mark.asyncio
    async def test_doctor_all_ok(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.commands.doctor.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine._load_dotenv"),
            patch("cliany_site.explorer.engine._normalize_openai_base_url", return_value=None),
            patch.dict(
                "os.environ",
                {
                    "CLIANY_ANTHROPIC_API_KEY": "test-key",
                    "CLIANY_LLM_PROVIDER": "anthropic",
                    "CLIANY_OPENAI_BASE_URL": "",
                },
            ),
        ):
            cs = ClanySite()
            mock_cdp = AsyncMock()
            mock_cdp.check_available = AsyncMock(return_value=True)
            cs._cdp = mock_cdp

            result = await cs.doctor()
            assert result["success"] is True
            checks = {item["name"]: item for item in result["data"]["checks"]}
            assert checks["cdp"]["status"] == "ok"
            assert checks["llm"]["status"] == "ok"
            assert result["data"]["summary"]["ready_for_existing_adapters"] is True

    @pytest.mark.asyncio
    async def test_doctor_cdp_fail(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.commands.doctor.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine._load_dotenv"),
            patch("cliany_site.explorer.engine._normalize_openai_base_url", return_value=None),
            patch.dict("os.environ", {"CLIANY_ANTHROPIC_API_KEY": "test-key"}, clear=False),
        ):
            cs = ClanySite()
            mock_cdp = AsyncMock()
            mock_cdp.check_available = AsyncMock(return_value=False)
            cs._cdp = mock_cdp

            result = await cs.doctor()
            assert result["success"] is False
            assert result["error"]["code"] == "E_CDP_UNAVAILABLE"
            assert result["error"]["details"] == result["data"]
            checks = {item["name"]: item for item in result["data"]["checks"]}
            assert checks["cdp"]["status"] == "fail"

    @pytest.mark.asyncio
    async def test_doctor_no_llm_key(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)

        env_clear = {
            "CLIANY_ANTHROPIC_API_KEY": "",
            "CLIANY_OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
            "CLIANY_LLM_PROVIDER": "anthropic",
            "CLIANY_OPENAI_BASE_URL": "",
        }

        with (
            patch("cliany_site.commands.doctor.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine._load_dotenv"),
            patch("cliany_site.explorer.engine._normalize_openai_base_url", return_value=None),
            patch.dict("os.environ", env_clear, clear=False),
        ):
            cs = ClanySite()
            mock_cdp = AsyncMock()
            mock_cdp.check_available = AsyncMock(return_value=True)
            cs._cdp = mock_cdp

            result = await cs.doctor()
            assert result["success"] is True
            checks = {item["name"]: item for item in result["data"]["checks"]}
            assert checks["llm"]["status"] == "warning"
            assert result["data"]["summary"]["ready_for_existing_adapters"] is True
            assert result["data"]["summary"]["ready_for_explore"] is False

    @pytest.mark.asyncio
    async def test_doctor_reuses_cli_checks_and_custom_port(self):
        from cliany_site.sdk import ClanySite

        cdp = object()
        diagnostics = {"checks": [], "summary": {"capabilities": {}}}
        result = {"ok": True, "data": diagnostics, "error": None}

        with (
            patch(
                "cliany_site.commands.doctor._run_checks",
                new_callable=AsyncMock,
                return_value=result,
            ) as run_checks,
            patch(
                "cliany_site.commands.doctor._require_capability",
                side_effect=lambda value, _capability: value,
            ),
        ):
            cs = ClanySite(port=9333)
            cs._cdp = cdp
            response = await cs.doctor(
                llm_live=True,
                require_capability="manage_adapters",
            )

        run_checks.assert_awaited_once_with(cdp, llm_live=True, port=9333)
        assert response == {"success": True, "data": diagnostics, "error": None}

    @pytest.mark.asyncio
    async def test_doctor_rejects_live_capability_without_preflight(self):
        from cliany_site.sdk import ClanySite

        result = await ClanySite().doctor(require_capability="generate_adapters")

        assert result["success"] is False
        assert result["error"]["code"] == "E_INVALID_PARAM"


# ═══════════════════════════════════════════════════════════
# SDK — list_adapters
# ═══════════════════════════════════════════════════════════


class TestSDKListAdapters:
    @pytest.mark.asyncio
    async def test_list_empty(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        with patch("cliany_site.loader.get_config", return_value=cfg):
            cs = ClanySite()
            result = await cs.list_adapters()
            assert result["success"] is True
            assert result["data"]["adapters"] == []
            assert result["data"]["count"] == 0

    @pytest.mark.asyncio
    async def test_list_with_adapters(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path, "example.com")

        with (
            patch("cliany_site.loader.get_config", return_value=cfg),
            patch("cliany_site.codegen.generator.get_config", return_value=cfg),
        ):
            cs = ClanySite()
            result = await cs.list_adapters()
            assert result["success"] is True
            assert "example.com" in result["data"]["adapters"]

    @pytest.mark.asyncio
    async def test_list_detail(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path, "example.com")

        with (
            patch("cliany_site.loader.get_config", return_value=cfg),
            patch("cliany_site.codegen.generator.get_config", return_value=cfg),
        ):
            cs = ClanySite()
            result = await cs.list_adapters(detail=True)
            assert result["success"] is True
            assert isinstance(result["data"]["adapters"], list)
            assert result["data"]["adapters"][0]["domain"] == "example.com"


# ═══════════════════════════════════════════════════════════
# SDK — verify
# ═══════════════════════════════════════════════════════════


class TestSDKVerify:
    @pytest.mark.asyncio
    async def test_verify_valid_adapter_without_starting_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().verify("test.com")

        assert result["success"] is True
        assert result["data"]["results"][0]["verdict"] == "ok"
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_missing_adapter_is_not_found(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        with patch("cliany_site.sdk.get_config", return_value=cfg):
            result = await ClanySite().verify("missing.example")

        assert result["success"] is False
        assert result["error"]["code"] == "ADAPTER_NOT_FOUND"
        assert result["error"]["details"] == {"domain": "missing.example"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "domain",
        [
            "",
            ".",
            "..",
            "../outside",
            "..\\outside",
            "/tmp/outside",
            "C:\\outside",
            "bad\x00name",
            7,
        ],
    )
    async def test_verify_rejects_unsafe_adapter_directory_names(self, domain):
        from cliany_site.sdk import ClanySite

        with (
            patch("cliany_site.sdk.get_config") as get_config,
            patch("cliany_site.commands.verify._verify_single") as verify_single,
        ):
            result = await ClanySite().verify(domain)

        assert result["success"] is False
        assert result["error"]["code"] == "E_INVALID_PARAM"
        get_config.assert_not_called()
        verify_single.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_static_failure_keeps_cli_results_contract(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "broken.example")
        (adapter_dir / "commands.py").unlink()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().verify("broken.example")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"] == {
            "domain": "broken.example",
            "results": [
                {
                    "domain": "broken.example",
                    "verdict": "commands_missing",
                    "issues": ["commands.py 不存在"],
                    "smoke": None,
                }
            ],
            "failed_domains": ["broken.example"],
        }
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_rejects_security_issue_before_importing_adapter(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "unsafe.example")
        imported_marker = tmp_path / "commands-imported"
        (adapter_dir / "commands.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(imported_marker)!r}).write_text('imported')\n"
            "import os\n"
            "os.system('true')\n",
            encoding="utf-8",
        )
        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().verify("unsafe.example")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        verified = result["error"]["details"]["results"][0]
        assert verified["verdict"] == "security_issue"
        assert any("os.system(" in issue for issue in verified["issues"])
        assert not imported_marker.exists()
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_rejects_non_utf8_commands_before_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "non-utf8.example")
        (adapter_dir / "commands.py").write_bytes(b"\xff\xfe")

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().verify("non-utf8.example")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        verified = result["error"]["details"]["results"][0]
        assert verified["verdict"] == "security_issue"
        assert verified["issues"] == ["commands.py 无法按 UTF-8 读取"]
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_rejects_symlinked_commands_before_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "linked.example")
        outside_commands = tmp_path / "outside-commands.py"
        outside_commands.write_text("import click\n", encoding="utf-8")
        (adapter_dir / "commands.py").unlink()
        (adapter_dir / "commands.py").symlink_to(outside_commands)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().verify("linked.example")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        verified = result["error"]["details"]["results"][0]
        assert verified["verdict"] == "security_issue"
        assert verified["issues"] == ["commands.py 不能是符号链接"]
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()


# ═══════════════════════════════════════════════════════════
# SDK — 同步 verify 便捷函数
# ═══════════════════════════════════════════════════════════


class TestSDKVerifySync:
    def test_verify_sync(self, tmp_path):
        from cliany_site.sdk import verify

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
        ):
            result = verify("test.com")

        assert result["success"] is True
        assert result["data"]["results"][0]["verdict"] == "ok"


# ═══════════════════════════════════════════════════════════
# SDK — execute
# ═══════════════════════════════════════════════════════════


class TestSDKExecute:
    @pytest.mark.asyncio
    async def test_execute_adapter_not_found(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        with patch("cliany_site.sdk.get_config", return_value=cfg):
            cs = ClanySite()
            result = await cs.execute("nonexistent.com", "search")
            assert result["success"] is False
            assert "ADAPTER_NOT_FOUND" in result["error"]["code"]

    @pytest.mark.asyncio
    async def test_execute_command_not_found(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            cs = ClanySite()
            result = await cs.execute("test.com", "nonexistent")
            assert result["success"] is False
            assert "COMMAND_NOT_FOUND" in result["error"]["code"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("commands_source", "metadata_source", "verdict", "reason"),
        [
            (None, '{"schema_version": 3}', "commands_missing", "commands.py 不存在"),
            (
                "import click\n",
                '{"schema_version": 3}',
                "commands_unloadable",
                "commands.py 必须导出 click.Group 类型的 cli",
            ),
            ("import click\n", "[]", "schema_error", "metadata.json 必须是 JSON object"),
        ],
    )
    async def test_execute_rejects_static_adapter_failures_before_browser(
        self,
        tmp_path,
        commands_source,
        metadata_source,
        verdict,
        reason,
    ):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = cfg.adapters_dir / "broken.example"
        adapter_dir.mkdir()
        if commands_source is not None:
            (adapter_dir / "commands.py").write_text(commands_source, encoding="utf-8")
        (adapter_dir / "metadata.json").write_text(metadata_source, encoding="utf-8")

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
            patch("cliany_site.action_runtime.execute_action_steps", new_callable=AsyncMock) as execute_steps,
        ):
            result = await ClanySite().execute("broken.example", "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"] == {
            "domain": "broken.example",
            "verdict": verdict,
            "reason": reason,
        }
        assert "cliany-site verify broken.example --strict --json" in result["error"]["fix"]
        ensure_browser.assert_not_awaited()
        execute_steps.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "domain",
        ["", ".", "..", "../outside", "..\\outside", "/tmp/outside", "C:\\outside", "bad\x00name", 7],
    )
    async def test_execute_rejects_unsafe_adapter_directory_names_before_lookup(self, domain):
        from cliany_site.sdk import ClanySite

        with patch("cliany_site.sdk.get_config") as get_config:
            result = await ClanySite().execute(domain, "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_INVALID_PARAM"
        get_config.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_rejects_security_issue_before_importing_adapter(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = cfg.adapters_dir / "unsafe.example"
        adapter_dir.mkdir()
        imported_marker = tmp_path / "commands-imported"
        (adapter_dir / "commands.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(imported_marker)!r}).write_text('imported')\n"
            "import os\n"
            "os.system('true')\n",
            encoding="utf-8",
        )
        (adapter_dir / "metadata.json").write_text(
            '{"schema_version": 3, "domain": "unsafe.example", "commands": []}',
            encoding="utf-8",
        )

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.loader.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().execute("unsafe.example", "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"]["verdict"] == "security_issue"
        assert "os.system(" in result["error"]["details"]["reason"]
        assert not imported_marker.exists()
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_non_utf8_commands_before_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = cfg.adapters_dir / "non-utf8.example"
        adapter_dir.mkdir()
        (adapter_dir / "commands.py").write_bytes(b"\xff\xfe")
        (adapter_dir / "metadata.json").write_text(
            '{"schema_version": 3, "domain": "non-utf8.example", "commands": []}',
            encoding="utf-8",
        )

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.loader.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().execute("non-utf8.example", "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"] == {
            "domain": "non-utf8.example",
            "verdict": "security_issue",
            "reason": "commands.py 无法按 UTF-8 读取",
        }
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_symlinked_commands_before_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "linked.example")
        outside_commands = tmp_path / "outside-commands.py"
        outside_commands.write_text("import click\n", encoding="utf-8")
        (adapter_dir / "commands.py").unlink()
        (adapter_dir / "commands.py").symlink_to(outside_commands)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.loader.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().execute("linked.example", "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"] == {
            "domain": "linked.example",
            "verdict": "security_issue",
            "reason": "commands.py 不能是符号链接",
        }
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_symlinked_manifest_before_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "linked-manifest.example")
        outside_manifest = tmp_path / "outside-manifest.json"
        outside_manifest.write_text("{}", encoding="utf-8")
        (adapter_dir / "manifest.json").symlink_to(outside_manifest)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.loader.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().execute("linked-manifest.example", "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"] == {
            "domain": "linked-manifest.example",
            "verdict": "security_issue",
            "reason": "manifest.json 不能是符号链接",
        }
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_rejects_symlinked_manifest_declared_file_before_browser(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        domain = "linked-declared-file.example"
        adapter_dir = _create_adapter_with_actions(tmp_path, domain)
        outside_notes = tmp_path / "outside-notes.txt"
        outside_notes.write_text("outside adapter file", encoding="utf-8")
        (adapter_dir / "notes.txt").symlink_to(outside_notes)
        _write_manifest(adapter_dir, domain, {"notes.txt": outside_notes})

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.loader.load_adapter_from_path") as load_adapter,
            patch.object(ClanySite, "_ensure_browser_session", new_callable=AsyncMock) as ensure_browser,
        ):
            result = await ClanySite().execute(domain, "search")

        assert result["success"] is False
        assert result["error"]["code"] == "E_VERIFY_STATIC"
        assert result["error"]["details"] == {
            "domain": domain,
            "verdict": "manifest_error",
            "reason": "已安装 adapter 的声明文件不能是符号链接: notes.txt",
        }
        load_adapter.assert_not_called()
        ensure_browser.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_success(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        mock_session = AsyncMock()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch("cliany_site.session.load_session", new_callable=AsyncMock),
            patch("cliany_site.action_runtime.execute_action_steps", new_callable=AsyncMock),
        ):
            cs = ClanySite()
            result = await cs.execute("test.com", "search")
            assert result["success"] is True
            assert result["data"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_with_params(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        mock_session = AsyncMock()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch("cliany_site.session.load_session", new_callable=AsyncMock),
            patch("cliany_site.action_runtime.execute_action_steps", new_callable=AsyncMock) as mock_exec,
        ):
            cs = ClanySite()
            result = await cs.execute("test.com", "search", params={"query": "hello"})
            assert result["success"] is True
            mock_exec.assert_awaited_once()
            call_kwargs = mock_exec.call_args
            assert call_kwargs.kwargs.get("params") == {"query": "hello"}

    @pytest.mark.asyncio
    async def test_execute_dry_run(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        mock_session = AsyncMock()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch("cliany_site.session.load_session", new_callable=AsyncMock),
            patch("cliany_site.action_runtime.execute_action_steps", new_callable=AsyncMock) as mock_exec,
        ):
            cs = ClanySite()
            result = await cs.execute("test.com", "search", dry_run=True)
            assert result["success"] is True
            assert result["data"]["dry_run"] is True
            call_kwargs = mock_exec.call_args
            assert call_kwargs.kwargs.get("dry_run") is True

    @pytest.mark.asyncio
    async def test_execute_failure(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path)

        mock_session = AsyncMock()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch("cliany_site.session.load_session", new_callable=AsyncMock),
            patch(
                "cliany_site.action_runtime.execute_action_steps",
                new_callable=AsyncMock,
                side_effect=RuntimeError("元素未找到"),
            ),
        ):
            cs = ClanySite()
            result = await cs.execute("test.com", "search")
            assert result["success"] is False
            assert "EXECUTION_FAILED" in result["error"]["code"]

    @pytest.mark.asyncio
    async def test_execute_empty_actions(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        adapter_dir = cfg.adapters_dir / "empty.com"
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "commands.py").write_text("import click\n", encoding="utf-8")
        metadata = {"command_defs": [{"name": "noop", "actions": []}]}
        (adapter_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            cs = ClanySite()
            result = await cs.execute("empty.com", "noop")
            assert result["success"] is False


# ═══════════════════════════════════════════════════════════
# SDK — explore
# ═══════════════════════════════════════════════════════════


class TestSDKExplore:
    @pytest.mark.asyncio
    async def test_explore_cdp_unavailable(self):
        from cliany_site.sdk import ClanySite

        with patch(
            "cliany_site.explorer.engine.WorkflowExplorer",
        ) as MockExplorer:
            mock_instance = MockExplorer.return_value
            mock_instance.explore = AsyncMock(side_effect=ConnectionError("CDP 不可用"))

            cs = ClanySite()
            result = await cs.explore("https://test.com", "测试工作流")
            assert result["success"] is False
            assert "CDP_UNAVAILABLE" in result["error"]["code"]

    @pytest.mark.asyncio
    async def test_explore_llm_error(self):
        from cliany_site.sdk import ClanySite

        with patch("cliany_site.explorer.engine.WorkflowExplorer") as MockExplorer:
            mock_instance = MockExplorer.return_value
            mock_instance.explore = AsyncMock(side_effect=OSError("请设置 CLIANY_OPENAI_API_KEY"))

            cs = ClanySite()
            result = await cs.explore("https://test.com", "测试")
            assert result["success"] is False
            assert "LLM_UNAVAILABLE" in result["error"]["code"]

    @pytest.mark.asyncio
    async def test_explore_data_quality_error_keeps_details(self):
        from cliany_site.errors import DataCommandQualityError
        from cliany_site.sdk import ClanySite

        details = {"repair_attempts": 1, "data_commands": [{"name": "search-results"}]}
        with patch("cliany_site.explorer.engine.WorkflowExplorer") as MockExplorer:
            mock_instance = MockExplorer.return_value
            mock_instance.explore = AsyncMock(
                side_effect=DataCommandQualityError("数据命令未通过提取质量门禁", details=details)
            )

            result = await ClanySite().explore("https://test.com", "测试")

        assert result["success"] is False
        assert result["error"]["code"] == "E_EMPTY_RESULT"
        assert result["error"]["details"] == details

    @pytest.mark.asyncio
    async def test_explore_success_create(self, tmp_path):
        from cliany_site.explorer.models import CommandSuggestion, ExploreResult, PageInfo
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)
        explore_result = ExploreResult(
            pages=[PageInfo(url="https://test.com", title="Test")],
            actions=[],
            commands=[CommandSuggestion(name="search", description="搜索", args=[], action_steps=[])],
        )

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine.WorkflowExplorer") as MockExplorer,
            patch("cliany_site.codegen.generator.AdapterGenerator") as MockGen,
            patch("cliany_site.codegen.generator.save_adapter", return_value=str(tmp_path / "commands.py")),
        ):
            mock_instance = MockExplorer.return_value
            mock_instance.explore = AsyncMock(return_value=explore_result)
            MockGen.return_value.generate.return_value = "# generated code"

            cs = ClanySite()
            result = await cs.explore("https://test.com", "搜索", force=True)
            assert result["success"] is True
            assert result["data"]["adapter_mode"] == "created"
            assert "search" in result["data"]["commands"]


# ═══════════════════════════════════════════════════════════
# SDK — login
# ═══════════════════════════════════════════════════════════


class TestSDKLogin:
    @pytest.mark.asyncio
    async def test_login_invalid_url(self):
        from cliany_site.sdk import ClanySite

        cs = ClanySite()
        result = await cs.login("")
        assert result["success"] is False
        assert "INVALID_URL" in result["error"]["code"]

    @pytest.mark.asyncio
    async def test_login_success(self):
        from cliany_site.sdk import ClanySite

        mock_session = AsyncMock()

        with (
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch(
                "cliany_site.session.save_session", new_callable=AsyncMock, return_value=("/path/to/session.json", 5)
            ),
        ):
            cs = ClanySite()
            result = await cs.login("https://github.com")
            assert result["success"] is True
            assert result["data"]["cookies_count"] == 5

    @pytest.mark.asyncio
    async def test_login_no_cookies(self):
        from cliany_site.sdk import ClanySite

        mock_session = AsyncMock()

        with (
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch(
                "cliany_site.session.save_session", new_callable=AsyncMock, return_value=("/path/to/session.json", 0)
            ),
        ):
            cs = ClanySite()
            result = await cs.login("https://github.com")
            assert result["success"] is False
            assert "NO_COOKIES" in result["error"]["code"]


# ═══════════════════════════════════════════════════════════
# SDK — navigate
# ═══════════════════════════════════════════════════════════


class TestSDKNavigate:
    @pytest.mark.asyncio
    async def test_navigate_success(self):
        from cliany_site.sdk import ClanySite

        mock_session = AsyncMock()

        with patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session):
            cs = ClanySite()
            result = await cs.navigate("https://example.com")
            assert result["success"] is True
            assert result["data"]["url"] == "https://example.com"
            mock_session.navigate_to.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_navigate_failure(self):
        from cliany_site.sdk import ClanySite

        mock_session = AsyncMock()
        mock_session.navigate_to = AsyncMock(side_effect=RuntimeError("timeout"))

        with patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session):
            cs = ClanySite()
            result = await cs.navigate("https://example.com")
            assert result["success"] is False


# ═══════════════════════════════════════════════════════════
# SDK — get_page_info
# ═══════════════════════════════════════════════════════════


class TestSDKGetPageInfo:
    @pytest.mark.asyncio
    async def test_get_page_info_success(self):
        from cliany_site.sdk import ClanySite

        mock_session = AsyncMock()
        mock_tree = {
            "url": "https://example.com",
            "title": "Example",
            "selector_map": {"0": {"name": "button"}, "1": {"name": "input"}},
        }

        with (
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch("cliany_site.browser.axtree.capture_axtree", new_callable=AsyncMock, return_value=mock_tree),
        ):
            cs = ClanySite()
            result = await cs.get_page_info()
            assert result["success"] is True
            assert result["data"]["elements_count"] == 2
            assert result["data"]["title"] == "Example"


# ═══════════════════════════════════════════════════════════
# SDK — save_session
# ═══════════════════════════════════════════════════════════


class TestSDKSaveSession:
    @pytest.mark.asyncio
    async def test_save_session_success(self):
        from cliany_site.sdk import ClanySite

        mock_session = AsyncMock()

        with (
            patch.object(ClanySite, "_ensure_browser_session", return_value=mock_session),
            patch(
                "cliany_site.session.save_session",
                new_callable=AsyncMock,
                return_value=("/path/session.json", 10),
            ),
        ):
            cs = ClanySite()
            result = await cs.save_session("test.com")
            assert result["success"] is True
            assert result["data"]["cookies_count"] == 10


# ═══════════════════════════════════════════════════════════
# SDK — 同步便捷函数
# ═══════════════════════════════════════════════════════════


class TestSyncFunctions:
    def test_list_adapters_sync(self, tmp_path):
        from cliany_site.sdk import list_adapters

        cfg = _make_config(tmp_path)
        with patch("cliany_site.loader.get_config", return_value=cfg):
            result = list_adapters()
            assert result["success"] is True
            assert result["data"]["count"] == 0

    def test_doctor_sync(self, tmp_path):
        from cliany_site.sdk import ClanySite, doctor

        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.commands.doctor.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine._load_dotenv"),
            patch("cliany_site.explorer.engine._normalize_openai_base_url", return_value=None),
            patch.dict(
                "os.environ",
                {
                    "CLIANY_ANTHROPIC_API_KEY": "test-key",
                    "CLIANY_LLM_PROVIDER": "anthropic",
                    "CLIANY_OPENAI_BASE_URL": "",
                },
            ),
            patch.object(ClanySite, "_ensure_cdp") as mock_ensure,
        ):
            mock_cdp = AsyncMock()
            mock_cdp.check_available = AsyncMock(return_value=True)
            mock_ensure.return_value = mock_cdp

            result = doctor()
            assert result["success"] is True

    def test_run_async_without_loop(self):
        from cliany_site.sdk import _run_async

        async def dummy():
            return 42

        assert _run_async(dummy()) == 42


# ═══════════════════════════════════════════════════════════
# HTTP API 服务器
# ═══════════════════════════════════════════════════════════


class TestAPIServer:
    def test_build_app(self):
        from cliany_site.server import APIServer

        server = APIServer(host="127.0.0.1", port=8080)
        app = server._build_app()
        assert app is not None

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        with patch("cliany_site.server.metadata.version", return_value="0.16.297"):
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/health")
                assert resp.status == 200
                data = await resp.json()

        assert data == {
            "status": "ok",
            "service": "cliany-site",
            "version": "0.16.297",
        }

    @pytest.mark.asyncio
    async def test_health_endpoint_handles_missing_distribution_metadata(self):
        from importlib.metadata import PackageNotFoundError

        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        with patch("cliany_site.server.metadata.version", side_effect=PackageNotFoundError):
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/health")
                assert resp.status == 200
                data = await resp.json()

        assert data["version"] == "unknown"

    @pytest.mark.asyncio
    async def test_adapters_endpoint(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.loader.get_config", return_value=cfg),
            patch("cliany_site.codegen.generator.get_config", return_value=cfg),
        ):
            server = APIServer()
            app = server._build_app()

            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/adapters")
                assert resp.status == 200
                data = await resp.json()
                assert data["success"] is True

    @pytest.mark.asyncio
    async def test_verify_endpoint_requires_domain_without_calling_sdk(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/verify")
            assert resp.status == 400
            data = await resp.json()
            assert data["error"]["code"] == "BAD_REQUEST"
        mock_sdk.verify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_endpoint_returns_real_static_failure(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "broken.example")
        (adapter_dir / "commands.py").unlink()
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
        ):
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/verify?domain=broken.example")
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        assert data["error"]["details"]["results"][0]["verdict"] == "commands_missing"

    @pytest.mark.asyncio
    async def test_verify_endpoint_returns_not_found_for_missing_adapter(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/verify?domain=missing.example")
                assert resp.status == 404
                data = await resp.json()

        assert data["error"]["code"] == "ADAPTER_NOT_FOUND"
        assert data["error"]["details"] == {"domain": "missing.example"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["../outside", "C:\\outside"])
    async def test_verify_endpoint_rejects_unsafe_adapter_directory_names(self, domain):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/verify", params={"domain": domain})
            assert resp.status == 400
            data = await resp.json()

        assert data["error"]["code"] == "E_INVALID_PARAM"

    @pytest.mark.asyncio
    async def test_verify_endpoint_maps_non_utf8_commands_to_unprocessable(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "non-utf8.example")
        (adapter_dir / "commands.py").write_bytes(b"\xff\xfe")
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
        ):
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/verify", params={"domain": "non-utf8.example"})
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        assert data["error"]["details"]["results"][0]["verdict"] == "security_issue"

    @pytest.mark.asyncio
    async def test_verify_endpoint_maps_symlinked_commands_to_unprocessable(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "linked.example")
        outside_commands = tmp_path / "outside-commands.py"
        outside_commands.write_text("import click\n", encoding="utf-8")
        (adapter_dir / "commands.py").unlink()
        (adapter_dir / "commands.py").symlink_to(outside_commands)
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.commands.verify.get_config", return_value=cfg),
        ):
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/verify", params={"domain": "linked.example"})
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        verified = data["error"]["details"]["results"][0]
        assert verified["verdict"] == "security_issue"
        assert verified["issues"] == ["commands.py 不能是符号链接"]

    @pytest.mark.asyncio
    async def test_doctor_endpoint(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        sdk = AsyncMock()
        sdk.doctor.return_value = {"success": True, "data": {"checks": []}, "error": None}
        server._sdk = sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/doctor")
            data = await resp.json()

        assert resp.status == 200
        assert data["success"] is True
        sdk.doctor.assert_awaited_once_with(llm_live=False, require_capability=None)

    @pytest.mark.asyncio
    async def test_doctor_endpoint_forwards_live_preflight_and_status(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        sdk = AsyncMock()
        sdk.doctor.return_value = {
            "success": False,
            "data": {"checks": [], "summary": {}},
            "error": {"code": "E_LLM_UNAVAILABLE", "message": "provider unavailable"},
        }
        server._sdk = sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.get(
                "/doctor?llm_live=true&require_capability=generate_adapters"
            )
            data = await resp.json()

        assert resp.status == 503
        assert data["error"]["code"] == "E_LLM_UNAVAILABLE"
        sdk.doctor.assert_awaited_once_with(
            llm_live=True,
            require_capability="generate_adapters",
        )

    @pytest.mark.asyncio
    async def test_doctor_endpoint_rejects_invalid_live_query(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        sdk = AsyncMock()
        server._sdk = sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/doctor?llm_live=maybe")
            data = await resp.json()

        assert resp.status == 400
        assert data["error"]["code"] == "BAD_REQUEST"
        sdk.doctor.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explore_missing_fields(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/explore", json={"url": "https://test.com"})
            assert resp.status == 400
            data = await resp.json()
            assert data["success"] is False

    @pytest.mark.asyncio
    async def test_execute_missing_fields(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/execute", json={"domain": "test.com"})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_login_missing_fields(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/login", json={})
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_explore_invalid_json(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/explore", data=b"not json", headers={"Content-Type": "application/json"})
            assert resp.status == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ["/explore", "/execute", "/login"])
    async def test_mutating_endpoints_reject_non_object_json(self, endpoint):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post(endpoint, json=["not", "an", "object"])
            assert resp.status == 400
            data = await resp.json()
            assert data["error"]["code"] == "BAD_REQUEST"
            assert "对象" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_execute_rejects_non_object_params_without_calling_sdk(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/execute",
                json={"domain": "test.com", "command": "search", "params": ["query", "cliany"]},
            )
            assert resp.status == 400
            data = await resp.json()
            assert data["error"]["code"] == "BAD_REQUEST"
            assert "params" in data["error"]["message"]
        mock_sdk.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_explore_rejects_non_boolean_force_without_calling_sdk(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/explore",
                json={"url": "https://test.com", "workflow": "搜索", "force": "false"},
            )
            assert resp.status == 400
            data = await resp.json()
            assert data["error"]["code"] == "BAD_REQUEST"
            assert "force" in data["error"]["message"]
        mock_sdk.explore.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_success(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        mock_sdk.execute = AsyncMock(return_value={"success": True, "data": {"status": "completed"}, "error": None})
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/execute", json={"domain": "test.com", "command": "search"})
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_execute_missing_adapter_is_not_found(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        mock_sdk.execute = AsyncMock(
            return_value={
                "success": False,
                "data": None,
                "error": {"code": "ADAPTER_NOT_FOUND", "message": "未找到 adapter"},
            }
        )
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/execute", json={"domain": "missing.example", "command": "search"})
            assert resp.status == 404
            data = await resp.json()
            assert data["error"]["code"] == "ADAPTER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_execute_static_adapter_failure_is_unprocessable(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = cfg.adapters_dir / "broken.example"
        adapter_dir.mkdir()
        (adapter_dir / "metadata.json").write_text('{"schema_version": 3}', encoding="utf-8")
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            async with TestClient(TestServer(app)) as client:
                resp = await client.post("/execute", json={"domain": "broken.example", "command": "search"})
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        assert data["error"]["details"] == {
            "domain": "broken.example",
            "verdict": "commands_missing",
            "reason": "commands.py 不存在",
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("domain", ["../outside", "C:\\outside"])
    async def test_execute_endpoint_rejects_unsafe_adapter_directory_names(self, domain):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/execute", json={"domain": domain, "command": "search"})
            assert resp.status == 400
            data = await resp.json()

        assert data["error"]["code"] == "E_INVALID_PARAM"

    @pytest.mark.asyncio
    async def test_execute_endpoint_maps_non_utf8_commands_to_unprocessable(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = cfg.adapters_dir / "non-utf8.example"
        adapter_dir.mkdir()
        (adapter_dir / "commands.py").write_bytes(b"\xff\xfe")
        (adapter_dir / "metadata.json").write_text(
            '{"schema_version": 3, "domain": "non-utf8.example", "commands": []}',
            encoding="utf-8",
        )
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/execute", json={"domain": "non-utf8.example", "command": "search"}
                )
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        assert data["error"]["details"]["verdict"] == "security_issue"

    @pytest.mark.asyncio
    async def test_execute_endpoint_maps_symlinked_commands_to_unprocessable(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "linked.example")
        outside_commands = tmp_path / "outside-commands.py"
        outside_commands.write_text("import click\n", encoding="utf-8")
        (adapter_dir / "commands.py").unlink()
        (adapter_dir / "commands.py").symlink_to(outside_commands)
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/execute", json={"domain": "linked.example", "command": "search"}
                )
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        assert data["error"]["details"] == {
            "domain": "linked.example",
            "verdict": "security_issue",
            "reason": "commands.py 不能是符号链接",
        }

    @pytest.mark.asyncio
    async def test_execute_endpoint_maps_symlinked_manifest_to_unprocessable(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.sdk import ClanySite
        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        adapter_dir = _create_adapter_with_actions(tmp_path, "linked-manifest.example")
        outside_manifest = tmp_path / "outside-manifest.json"
        outside_manifest.write_text("{}", encoding="utf-8")
        (adapter_dir / "manifest.json").symlink_to(outside_manifest)
        server = APIServer()
        server._sdk = ClanySite()
        app = server._build_app()

        with patch("cliany_site.sdk.get_config", return_value=cfg):
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/execute", json={"domain": "linked-manifest.example", "command": "search"}
                )
                assert resp.status == 422
                data = await resp.json()

        assert data["error"]["code"] == "E_VERIFY_STATIC"
        assert data["error"]["details"] == {
            "domain": "linked-manifest.example",
            "verdict": "security_issue",
            "reason": "manifest.json 不能是符号链接",
        }

    @pytest.mark.asyncio
    async def test_explore_unavailable_provider_returns_service_unavailable(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        mock_sdk.explore = AsyncMock(
            return_value={
                "success": False,
                "data": None,
                "error": {"code": "E_LLM_UNAVAILABLE", "message": "provider unavailable"},
            }
        )
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/explore", json={"url": "https://test.com", "workflow": "搜索"})
            assert resp.status == 503
            data = await resp.json()
            assert data["error"]["code"] == "E_LLM_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_login_success(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        mock_sdk.login = AsyncMock(return_value={"success": True, "data": {"cookies_count": 5}, "error": None})
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/login", json={"url": "https://github.com"})
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_explore_success(self):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        mock_sdk.explore = AsyncMock(
            return_value={"success": True, "data": {"domain": "test.com", "commands": ["search"]}, "error": None}
        )
        server._sdk = mock_sdk
        app = server._build_app()

        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/explore", json={"url": "https://test.com", "workflow": "搜索"})
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_adapters_detail(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)
        _create_adapter_with_actions(tmp_path, "example.com")

        with (
            patch("cliany_site.loader.get_config", return_value=cfg),
            patch("cliany_site.codegen.generator.get_config", return_value=cfg),
        ):
            server = APIServer()
            app = server._build_app()

            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/adapters?detail=true")
                assert resp.status == 200
                data = await resp.json()
                assert data["success"] is True
                assert isinstance(data["data"]["adapters"], list)

    @pytest.mark.asyncio
    async def test_cleanup(self):
        from cliany_site.server import APIServer

        server = APIServer()
        mock_sdk = AsyncMock()
        server._sdk = mock_sdk
        await server._cleanup(None)
        mock_sdk.close.assert_awaited_once()
        assert server._sdk is None

    @pytest.mark.asyncio
    async def test_cleanup_no_sdk(self):
        from cliany_site.server import APIServer

        server = APIServer()
        await server._cleanup(None)
        assert server._sdk is None


# ═══════════════════════════════════════════════════════════
# CLI — serve 命令
# ═══════════════════════════════════════════════════════════


class TestServeCLI:
    def test_serve_command_exists(self):
        from cliany_site.cli import cli

        runner = __import__("click.testing", fromlist=["CliRunner"]).CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "HTTP API" in result.output or "绑定地址" in result.output

    def test_serve_passes_root_browser_options_to_api_server(self):
        from cliany_site.cli import cli

        runner = __import__("click.testing", fromlist=["CliRunner"]).CliRunner()
        with patch("cliany_site.server.APIServer") as server_class:
            result = runner.invoke(
                cli,
                ["--headless", "--cdp-url", "ws://chrome:9222", "serve", "--host", "0.0.0.0", "--port", "8081"],
            )

        assert result.exit_code == 0, result.output
        server_class.assert_called_once_with(
            host="0.0.0.0",
            port=8081,
            cdp_url="ws://chrome:9222",
            headless=True,
        )
        server_class.return_value.run.assert_called_once_with()


# ═══════════════════════════════════════════════════════════
# __init__.py 导出
# ═══════════════════════════════════════════════════════════


class TestPackageExports:
    def test_public_api_importable(self):
        from cliany_site import ClanySite, doctor, execute, explore, list_adapters, login, verify

        assert ClanySite is not None
        assert callable(explore)
        assert callable(execute)
        assert callable(login)
        assert callable(doctor)
        assert callable(list_adapters)
        assert callable(verify)

    def test_package_version_matches_installed_distribution(self):
        from importlib.metadata import version

        from cliany_site import __version__

        assert __version__ == version("cliany-site")
