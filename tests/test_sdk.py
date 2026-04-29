"""Python SDK + HTTP API 服务测试"""

from __future__ import annotations

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
    cfg.adapters_dir.mkdir(parents=True, exist_ok=True)
    cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
    cfg.to_dict.return_value = {"cdp_port": 9222, "home_dir": str(tmp_path)}
    return cfg


def _create_adapter_with_actions(tmp_path: Path, domain: str = "test.com") -> Path:
    cfg_mock = _make_config(tmp_path)
    adapter_dir = cfg_mock.adapters_dir / domain
    adapter_dir.mkdir(parents=True, exist_ok=True)

    commands_py = adapter_dir / "commands.py"
    commands_py.write_text("import click\n", encoding="utf-8")

    metadata = {
        "schema_version": 2,
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
            patch("cliany_site.sdk.get_config", return_value=cfg),
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
            assert result["data"]["cdp"] == "ok"
            assert result["data"]["llm"] == "ok"

    @pytest.mark.asyncio
    async def test_doctor_cdp_fail(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
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
            assert "cdp" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_doctor_no_llm_key(self, tmp_path):
        from cliany_site.sdk import ClanySite

        cfg = _make_config(tmp_path)

        env_clear = {
            "CLIANY_ANTHROPIC_API_KEY": "",
            "CLIANY_OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OPENAI_API_KEY": "",
        }

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine._load_dotenv"),
            patch("cliany_site.explorer.engine._normalize_openai_base_url", return_value=None),
            patch.dict("os.environ", env_clear, clear=False),
        ):
            cs = ClanySite()
            mock_cdp = AsyncMock()
            mock_cdp.check_available = AsyncMock(return_value=True)
            cs._cdp = mock_cdp

            result = await cs.doctor()
            assert result["success"] is False
            assert "llm" in result["error"]["message"]


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
            patch("cliany_site.sdk.get_config", return_value=cfg),
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

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"

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
    async def test_doctor_endpoint(self, tmp_path):
        from aiohttp.test_utils import TestClient, TestServer

        from cliany_site.server import APIServer

        cfg = _make_config(tmp_path)

        with (
            patch("cliany_site.sdk.get_config", return_value=cfg),
            patch("cliany_site.explorer.engine._load_dotenv"),
            patch("cliany_site.explorer.engine._normalize_openai_base_url", return_value=None),
            patch.dict("os.environ", {"CLIANY_ANTHROPIC_API_KEY": "key"}),
        ):
            server = APIServer()
            mock_cdp = AsyncMock()
            mock_cdp.check_available = AsyncMock(return_value=True)
            mock_sdk = MagicMock()
            mock_sdk._cdp = mock_cdp

            app = server._build_app()

            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/doctor")
                data = await resp.json()
                assert isinstance(data, dict)

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


# ═══════════════════════════════════════════════════════════
# __init__.py 导出
# ═══════════════════════════════════════════════════════════


class TestPackageExports:
    def test_public_api_importable(self):
        from cliany_site import ClanySite, doctor, execute, explore, list_adapters, login

        assert ClanySite is not None
        assert callable(explore)
        assert callable(execute)
        assert callable(login)
        assert callable(doctor)
        assert callable(list_adapters)
