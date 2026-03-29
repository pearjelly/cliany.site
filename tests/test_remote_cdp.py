import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from cliany_site.browser.cdp import CDPConnection, _parse_cdp_url, cdp_from_context
from cliany_site.config import ClanySiteConfig, load_config


class TestParseCdpUrl:
    def test_ws_url(self):
        host, port = _parse_cdp_url("ws://192.168.1.100:9222")
        assert host == "192.168.1.100"
        assert port == 9222

    def test_http_url(self):
        host, port = _parse_cdp_url("http://remote-host:9333")
        assert host == "remote-host"
        assert port == 9333

    def test_bare_host_port(self):
        host, port = _parse_cdp_url("10.0.0.5:9222")
        assert host == "10.0.0.5"
        assert port == 9222

    def test_default_port(self):
        host, port = _parse_cdp_url("http://myhost")
        assert host == "myhost"
        assert port == 9222

    def test_whitespace_stripped(self):
        host, port = _parse_cdp_url("  ws://host:1234  ")
        assert host == "host"
        assert port == 1234

    def test_localhost(self):
        host, port = _parse_cdp_url("http://localhost:9222")
        assert host == "localhost"
        assert port == 9222


class TestCDPConnectionInit:
    def test_defaults(self):
        cdp = CDPConnection()
        assert cdp._cdp_url == ""
        assert cdp._headless is False
        assert cdp.is_remote is False

    def test_explicit_cdp_url(self):
        cdp = CDPConnection(cdp_url="ws://remote:9222")
        assert cdp._cdp_url == "ws://remote:9222"
        assert cdp.is_remote is True

    def test_explicit_headless(self):
        cdp = CDPConnection(headless=True)
        assert cdp._headless is True

    def test_config_fallback(self, monkeypatch):
        monkeypatch.setenv("CLIANY_CDP_URL", "ws://env-host:8888")
        monkeypatch.setenv("CLIANY_HEADLESS", "true")
        from cliany_site.config import reset_config

        reset_config()
        cdp = CDPConnection()
        assert cdp._cdp_url == "ws://env-host:8888"
        assert cdp._headless is True

    def test_explicit_overrides_config(self, monkeypatch):
        monkeypatch.setenv("CLIANY_CDP_URL", "ws://env-host:8888")
        from cliany_site.config import reset_config

        reset_config()
        cdp = CDPConnection(cdp_url="ws://explicit:9222")
        assert cdp._cdp_url == "ws://explicit:9222"


class TestIsRemote:
    def test_empty_url_is_not_remote(self):
        cdp = CDPConnection(cdp_url="")
        assert cdp.is_remote is False

    def test_none_url_is_not_remote(self):
        cdp = CDPConnection(cdp_url=None)
        assert cdp.is_remote is False

    def test_localhost_is_not_remote(self):
        cdp = CDPConnection(cdp_url="http://localhost:9222")
        assert cdp.is_remote is False

    def test_127_is_not_remote(self):
        cdp = CDPConnection(cdp_url="http://127.0.0.1:9222")
        assert cdp.is_remote is False

    def test_ipv6_loopback_is_not_remote(self):
        cdp = CDPConnection(cdp_url="http://[::1]:9222")
        assert cdp.is_remote is False

    def test_other_host_is_remote(self):
        cdp = CDPConnection(cdp_url="ws://192.168.1.50:9222")
        assert cdp.is_remote is True


class TestResolveHostPort:
    def test_uses_cdp_url_when_set(self):
        cdp = CDPConnection(cdp_url="http://myhost:7777")
        host, port = cdp._resolve_host_port()
        assert host == "myhost"
        assert port == 7777

    def test_uses_cdp_url_ignores_port_arg(self):
        cdp = CDPConnection(cdp_url="http://myhost:7777")
        host, port = cdp._resolve_host_port(port=5555)
        assert host == "myhost"
        assert port == 7777

    def test_falls_back_to_localhost_with_port(self):
        cdp = CDPConnection()
        host, port = cdp._resolve_host_port(port=4444)
        assert host == "localhost"
        assert port == 4444

    def test_falls_back_to_config_port(self):
        cdp = CDPConnection()
        host, port = cdp._resolve_host_port()
        assert host == "localhost"
        assert port == 9222


class TestCheckAvailableRemote:
    def test_remote_uses_probe(self):
        cdp = CDPConnection(cdp_url="ws://remote-server:9222")

        async def run():
            with patch.object(cdp, "_probe_remote", new_callable=AsyncMock, return_value=True) as mock_probe:
                result = await cdp.check_available()
                assert result is True
                mock_probe.assert_called_once_with("remote-server", 9222)

        asyncio.run(run())

    def test_remote_probe_failure(self):
        cdp = CDPConnection(cdp_url="ws://unreachable:9222")

        async def run():
            with patch.object(cdp, "_probe_remote", new_callable=AsyncMock, return_value=False):
                result = await cdp.check_available()
                assert result is False

        asyncio.run(run())

    def test_local_uses_ensure_chrome(self):
        cdp = CDPConnection()

        async def run():
            with patch("cliany_site.browser.cdp.ensure_chrome", return_value=("ws://...", None)):
                result = await cdp.check_available()
                assert result is True

        asyncio.run(run())


class TestConnectRemote:
    def test_connect_sets_is_local_false_for_remote(self):
        cdp = CDPConnection(cdp_url="ws://remote:9222")

        async def run():
            with patch("cliany_site.browser.cdp.BrowserSession") as mock_session_cls:
                mock_instance = MagicMock()
                mock_instance.start = AsyncMock()
                mock_session_cls.return_value = mock_instance

                with patch("cliany_site.browser.cdp.BrowserProfile") as mock_profile_cls:
                    await cdp.connect()
                    mock_profile_cls.assert_called_once_with(
                        cdp_url="http://remote:9222",
                        is_local=False,
                    )

        asyncio.run(run())

    def test_connect_sets_is_local_true_for_localhost(self):
        cdp = CDPConnection()

        async def run():
            with patch("cliany_site.browser.cdp.BrowserSession") as mock_session_cls:
                mock_instance = MagicMock()
                mock_instance.start = AsyncMock()
                mock_session_cls.return_value = mock_instance

                with patch("cliany_site.browser.cdp.BrowserProfile") as mock_profile_cls:
                    await cdp.connect()
                    mock_profile_cls.assert_called_once_with(
                        cdp_url="http://localhost:9222",
                        is_local=True,
                    )

        asyncio.run(run())


class TestCdpFromContext:
    def test_from_click_context(self):
        mock_root = MagicMock()
        mock_root.obj = {"cdp_url": "ws://ctx-host:9222", "headless": True}

        mock_ctx = MagicMock()
        mock_ctx.find_root.return_value = mock_root

        cdp = cdp_from_context(mock_ctx)
        assert cdp._cdp_url == "ws://ctx-host:9222"
        assert cdp._headless is True

    def test_from_dict(self):
        obj = {"cdp_url": "ws://dict-host:9222", "headless": False}
        cdp = cdp_from_context(obj)
        assert cdp._cdp_url == "ws://dict-host:9222"
        assert cdp._headless is False

    def test_from_empty_context(self):
        mock_root = MagicMock()
        mock_root.obj = {}
        mock_ctx = MagicMock()
        mock_ctx.find_root.return_value = mock_root

        cdp = cdp_from_context(mock_ctx)
        assert cdp._cdp_url == ""
        assert cdp._headless is False

    def test_from_none_values(self):
        mock_root = MagicMock()
        mock_root.obj = {"cdp_url": None, "headless": None}
        mock_ctx = MagicMock()
        mock_ctx.find_root.return_value = mock_root

        cdp = cdp_from_context(mock_ctx)
        assert cdp._cdp_url == ""


class TestConfigCdpUrlAndHeadless:
    def test_defaults(self):
        cfg = ClanySiteConfig()
        assert cfg.cdp_url == ""
        assert cfg.headless is False

    def test_env_cdp_url(self, monkeypatch):
        monkeypatch.setenv("CLIANY_CDP_URL", "ws://env:9222")
        from cliany_site.config import reset_config

        reset_config()
        cfg = load_config()
        assert cfg.cdp_url == "ws://env:9222"

    def test_env_headless(self, monkeypatch):
        monkeypatch.setenv("CLIANY_HEADLESS", "true")
        from cliany_site.config import reset_config

        reset_config()
        cfg = load_config()
        assert cfg.headless is True

    def test_to_dict_contains_new_fields(self):
        cfg = ClanySiteConfig(cdp_url="ws://host:9222", headless=True)
        d = cfg.to_dict()
        assert d["cdp_url"] == "ws://host:9222"
        assert d["headless"] is True


class TestEnsureChromeHeadless:
    def test_headless_passed_to_launch(self):
        with (
            patch("cliany_site.browser.launcher.detect_running_chrome", side_effect=[None, "ws://..."]),
            patch("cliany_site.browser.launcher.launch_chrome") as mock_launch,
        ):
            mock_proc = MagicMock()
            mock_launch.return_value = mock_proc

            from cliany_site.browser.launcher import ensure_chrome

            _, proc = ensure_chrome(port=9222, headless=True)
            mock_launch.assert_called_once_with(9222, headless=True)
            assert proc is mock_proc

    def test_headless_false_by_default(self):
        with (
            patch("cliany_site.browser.launcher.detect_running_chrome", side_effect=[None, "ws://..."]),
            patch("cliany_site.browser.launcher.launch_chrome") as mock_launch,
        ):
            mock_proc = MagicMock()
            mock_launch.return_value = mock_proc

            from cliany_site.browser.launcher import ensure_chrome

            ensure_chrome(port=9222)
            mock_launch.assert_called_once_with(9222, headless=False)

    def test_skip_launch_if_already_running(self):
        with patch("cliany_site.browser.launcher.detect_running_chrome", return_value="ws://..."):
            from cliany_site.browser.launcher import ensure_chrome

            ws_url, proc = ensure_chrome(port=9222, headless=True)
            assert ws_url == "ws://..."
            assert proc is None


class TestGetPagesRemote:
    def test_uses_remote_host(self):
        cdp = CDPConnection(cdp_url="http://remote:9333")

        async def run():
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=[{"id": "1"}])
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)

            mock_session = MagicMock()
            mock_session.get = MagicMock(return_value=mock_resp)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with patch("cliany_site.browser.cdp.aiohttp.ClientSession", return_value=mock_session):
                pages = await cdp.get_pages()
                assert len(pages) == 1
                mock_session.get.assert_called_once()
                call_url = mock_session.get.call_args[0][0]
                assert "remote:9333" in call_url

        asyncio.run(run())
