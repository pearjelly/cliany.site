"""
Spike T01 결론: 방안 A 채택.
BrowserSession.cdp_client.send.Network.enable(session_id=...) 및
BrowserSession.cdp_client.send.Console.enable(session_id=...) 로
CDP 도메인 활성화 가능. 방안 B (cdp_raw.py) 불필요.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def mock_browser_session():
    session = MagicMock()
    session.cdp_client.send.Network.enable = AsyncMock(return_value={})
    session.cdp_client.send.Console.enable = AsyncMock(return_value={})
    return session


class TestNetworkEnable:
    async def test_network_enable_calls_cdp(self, mock_browser_session):
        from cliany_site.browser.cdp import enable_network_capture

        await enable_network_capture(mock_browser_session)

        mock_browser_session.cdp_client.send.Network.enable.assert_called_once()

    async def test_network_enable_forwards_session_id(self, mock_browser_session):
        from cliany_site.browser.cdp import enable_network_capture

        await enable_network_capture(mock_browser_session, session_id="abc-session-123")

        mock_browser_session.cdp_client.send.Network.enable.assert_called_once_with(
            session_id="abc-session-123"
        )

    async def test_network_enable_no_session_id_passes_none(self, mock_browser_session):
        from cliany_site.browser.cdp import enable_network_capture

        await enable_network_capture(mock_browser_session)

        call_args = mock_browser_session.cdp_client.send.Network.enable.call_args
        assert call_args.kwargs.get("session_id") is None


class TestConsoleEnable:
    async def test_console_enable_calls_cdp(self, mock_browser_session):
        from cliany_site.browser.cdp import enable_console_capture

        await enable_console_capture(mock_browser_session)

        mock_browser_session.cdp_client.send.Console.enable.assert_called_once()

    async def test_console_enable_forwards_session_id(self, mock_browser_session):
        from cliany_site.browser.cdp import enable_console_capture

        await enable_console_capture(mock_browser_session, session_id="sess-xyz-456")

        mock_browser_session.cdp_client.send.Console.enable.assert_called_once_with(
            session_id="sess-xyz-456"
        )

    async def test_console_enable_no_session_id_passes_none(self, mock_browser_session):
        from cliany_site.browser.cdp import enable_console_capture

        await enable_console_capture(mock_browser_session)

        call_args = mock_browser_session.cdp_client.send.Console.enable.call_args
        assert call_args.kwargs.get("session_id") is None


class TestPlanAApiContract:
    def test_cdp_use_network_library_exists(self):
        from cdp_use.cdp.network.library import NetworkClient  # noqa: F401

    def test_cdp_use_console_library_exists(self):
        from cdp_use.cdp.console.library import ConsoleClient  # noqa: F401

    def test_cdp_library_has_network_and_console(self):
        import inspect

        from cdp_use.cdp.library import CDPLibrary

        source = inspect.getsource(CDPLibrary.__init__)
        assert "Network" in source
        assert "Console" in source

    def test_browser_session_has_cdp_client_property(self):
        from browser_use.browser.session import BrowserSession

        assert hasattr(BrowserSession, "cdp_client")
