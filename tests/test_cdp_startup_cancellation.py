import asyncio
from unittest.mock import MagicMock

import pytest

from cliany_site.browser import cdp as cdp_module


@pytest.mark.asyncio
@pytest.mark.parametrize("created_here", [True, False])
async def test_pending_cancellation_at_sync_startup_handoff_only_cleans_new_browser(monkeypatch, created_here):
    process = MagicMock()
    process.poll.return_value = None
    connection = cdp_module.CDPConnection(cdp_url="http://127.0.0.1:48801")

    def cancelled_startup(*args, **kwargs):
        asyncio.current_task().cancel()
        return "ws://127.0.0.1:48801/browser/test", process if created_here else None

    monkeypatch.setattr(cdp_module, "ensure_chrome", cancelled_startup)
    task = asyncio.create_task(connection.check_available())
    with pytest.raises(asyncio.CancelledError):
        await task
    if created_here:
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)
        assert connection._chrome_proc is None
        assert connection._chrome_auto_launched is False
    else:
        process.terminate.assert_not_called()
        process.wait.assert_not_called()
