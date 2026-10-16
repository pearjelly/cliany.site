import asyncio
import sys
import time
from contextlib import suppress
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest

from cliany_site.commands.browser.type_cmd import _run_type

TREE = {"selector_map": {"2": {"ref": "2", "role": "textbox", "name": "Search"}}}


@pytest.fixture
def typing_context(monkeypatch, tmp_home, clean_env):
    monkeypatch.setenv("CLIANY_RESOLVE_RETRY_DELAY", "0.005")
    monkeypatch.setattr("cliany_site.commands.browser.type_cmd._TYPE_TARGET_TIMEOUT_SECONDS", 0.05, raising=False)
    session = MagicMock()
    session.get_element_by_index = AsyncMock(return_value=object())
    session.event_bus.dispatch.side_effect = lambda event: event
    cdp = MagicMock()
    cdp.check_available = AsyncMock(return_value=True)
    cdp.connect = AsyncMock(return_value=session)
    cdp.disconnect = AsyncMock()

    class Event:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.event_result = AsyncMock()

        def __await__(self):
            return iter(())

    events = ModuleType("browser_use.browser.events")
    events.TypeTextEvent = Event
    monkeypatch.setitem(sys.modules, "browser_use.browser.events", events)
    return cdp, session


@pytest.mark.asyncio
async def test_named_type_observes_again_before_dispatching_once(monkeypatch, typing_context):
    cdp, session = typing_context
    capture = AsyncMock(side_effect=[{"selector_map": {}}, TREE])
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    result = await _run_type(cdp, None, "Search", "Gamma", False, True, role="textbox")
    assert result["ok"] is True
    assert capture.await_count == 2
    session.event_bus.dispatch.assert_called_once()
    assert session.event_bus.dispatch.call_args.args[0].kwargs["text"] == "Gamma"
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_named_type_stays_bounded_without_dispatch(monkeypatch, typing_context):
    cdp, session = typing_context
    capture = AsyncMock(return_value={"selector_map": {}})
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    started = time.monotonic()
    result = await _run_type(cdp, None, "Search", "Gamma", False, True)
    assert result["ok"] is False and result["error"]["code"] == "E_SELECTOR_NOT_FOUND"
    assert capture.await_count >= 2 and time.monotonic() - started < 0.5
    session.event_bus.dispatch.assert_not_called()
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("late_success", [False, True])
async def test_type_probe_cannot_dispatch_after_its_deadline(monkeypatch, typing_context, late_success):
    cdp, session = typing_context

    async def capture(_session):
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            if not late_success:
                raise
        return TREE

    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    started = time.monotonic()
    result = await _run_type(cdp, None, "Search", "Gamma", False, True)
    assert result["ok"] is False and time.monotonic() - started < 0.5
    session.event_bus.dispatch.assert_not_called()
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_late_node_lookup_does_not_dispatch(monkeypatch, typing_context):
    cdp, session = typing_context

    async def get_node(_index):
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(1)
        return object()

    session.get_element_by_index.side_effect = get_node
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", AsyncMock(return_value=TREE))
    result = await _run_type(cdp, None, "Search", "Gamma", False, True)
    assert result["ok"] is False
    session.event_bus.dispatch.assert_not_called()
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_explicit_ref_is_not_retargeted_in_a_later_snapshot(monkeypatch, typing_context):
    cdp, session = typing_context
    capture = AsyncMock(side_effect=[{"selector_map": {}}, TREE])
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    result = await _run_type(cdp, "2", None, "Gamma", False, True)
    assert result["ok"] is False and capture.await_count == 1
    session.event_bus.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_tied_named_type_never_mutates_either_field(monkeypatch, typing_context):
    cdp, session = typing_context
    tree = {"selector_map": {**TREE["selector_map"], "3": {"ref": "3", "role": "textbox", "name": "Search"}}}
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", AsyncMock(return_value=tree))
    result = await _run_type(cdp, None, "Search", "Gamma", False, True, role="textbox")
    assert result["ok"] is False and result["error"]["code"] == "E_SELECTOR_NOT_FOUND"
    session.get_element_by_index.assert_not_awaited()
    session.event_bus.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_type_challenge_stops_observation_immediately(monkeypatch, typing_context):
    cdp, session = typing_context
    capture = AsyncMock(side_effect=[{"title": "Client Challenge", "selector_map": {}}, TREE])
    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    result = await _run_type(cdp, None, "Search", "Gamma", False, True)
    assert result["error"]["code"] == "E_PAGE_NOT_READY" and capture.await_count == 1
    session.event_bus.dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_type_cancellation_propagates_and_disconnects(monkeypatch, typing_context):
    cdp, session = typing_context
    entered = asyncio.Event()

    async def capture(_session):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("cliany_site.browser.axtree.capture_axtree", capture)
    task = asyncio.create_task(_run_type(cdp, None, "Search", "Gamma", False, True))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    session.event_bus.dispatch.assert_not_called()
    cdp.disconnect.assert_awaited_once()
