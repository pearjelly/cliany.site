import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock

import pytest

from cliany_site.browser.cdp import CDPConnection


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [ValueError("stop failed"), asyncio.CancelledError()])
async def test_disconnect_failure_still_reaps_owned_browser(error, tmp_home):
    connection = CDPConnection()
    session = MagicMock(stop=AsyncMock(side_effect=error))
    process = MagicMock()
    process.poll.return_value = None
    connection._session = session
    connection._chrome_proc = process
    connection._chrome_auto_launched = True

    with pytest.raises(type(error)) as caught:
        await connection.disconnect()

    assert caught.value is error
    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=5)
    assert connection._session is None
    assert connection._chrome_proc is None
    assert connection._chrome_auto_launched is False
    await connection.disconnect()
    session.stop.assert_awaited_once()
    process.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_reaps_after_terminate_timeout(tmp_home):
    connection = CDPConnection()
    process = MagicMock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired("chrome", 5), None]
    connection._chrome_proc = process
    connection._chrome_auto_launched = True

    await connection.disconnect()

    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()
    assert process.wait.call_count == 2
    assert connection._chrome_proc is None
    assert connection._chrome_auto_launched is False


@pytest.mark.asyncio
async def test_disconnect_cleanup_failure_preserves_session_error(tmp_home):
    connection = CDPConnection()
    error = ValueError("stop failed")
    connection._session = MagicMock(stop=AsyncMock(side_effect=error))
    process = MagicMock()
    process.poll.return_value = None
    process.terminate.side_effect = OSError("cleanup failed")
    connection._chrome_proc = process

    with pytest.raises(ValueError) as caught:
        await connection.disconnect()

    assert caught.value is error
    assert connection._session is None
    assert connection._chrome_proc is None


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [None, OSError("stop failed"), TimeoutError(), RuntimeError("stop failed")])
async def test_disconnect_preserves_handled_stop_errors(error, tmp_home):
    connection = CDPConnection()
    connection._session = MagicMock(stop=AsyncMock(side_effect=error))
    process = MagicMock()
    process.poll.return_value = None
    connection._chrome_proc = process
    connection._chrome_auto_launched = True

    await connection.disconnect()

    process.terminate.assert_called_once_with()
    assert connection._session is None
    assert connection._chrome_proc is None
    assert connection._chrome_auto_launched is False


@pytest.mark.asyncio
async def test_disconnect_external_browser_has_no_owned_process(tmp_home):
    connection = CDPConnection(cdp_url="http://127.0.0.1:48801")
    error = asyncio.CancelledError()
    session = MagicMock(stop=AsyncMock(side_effect=error))
    connection._session = session

    with pytest.raises(asyncio.CancelledError) as caught:
        await connection.disconnect()

    assert caught.value is error
    session.stop.assert_awaited_once()
    assert connection._session is None
    assert connection._chrome_proc is None
