from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cliany_site.commands.browser.select_cmd import _run_select
from cliany_site.commands.browser.submit_cmd import _run_submit
from cliany_site.commands.browser.click_cmd import _run_click
from cliany_site.commands.browser.type_cmd import _run_type


class _AwaitableEvent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.event_result = AsyncMock(return_value=None)

    def __await__(self):
        async def _wait():
            return self

        return _wait().__await__()


def _fake_events_module() -> ModuleType:
    module = ModuleType("browser_use.browser.events")
    module.SelectDropdownOptionEvent = type("SelectDropdownOptionEvent", (_AwaitableEvent,), {})
    module.ClickElementEvent = type("ClickElementEvent", (_AwaitableEvent,), {})
    module.TypeTextEvent = type("TypeTextEvent", (_AwaitableEvent,), {})
    module.SendKeysEvent = type("SendKeysEvent", (_AwaitableEvent,), {})
    return module


def _cdp_with_node() -> tuple[MagicMock, MagicMock]:
    cdp = MagicMock()
    cdp.check_available = AsyncMock(return_value=True)
    cdp.disconnect = AsyncMock()
    session = MagicMock()
    session.get_element_by_index = AsyncMock(return_value=object())
    session.event_bus.dispatch.side_effect = lambda event: event
    cdp.connect = AsyncMock(return_value=session)
    return cdp, session


@pytest.mark.asyncio
@pytest.mark.parametrize("clear", [False, True])
@pytest.mark.parametrize("submit", [False, True])
@pytest.mark.parametrize("value", ["hello", ""])
async def test_type_dispatches_flags_and_waits_for_handlers(monkeypatch, tmp_home, clear, submit, value):
    cdp, session = _cdp_with_node()
    monkeypatch.setitem(sys.modules, "browser_use.browser.events", _fake_events_module())
    with patch("cliany_site.browser.axtree.capture_axtree", new=AsyncMock(return_value=_TREE)):
        result = await _run_type(cdp, None, "Search", value, submit, clear)
    assert result["ok"] is True
    session.get_element_by_index.assert_awaited_once_with(2)
    events = [call.args[0] for call in session.event_bus.dispatch.call_args_list]
    assert len(events) == 1 + int(submit)
    event = events[0]
    if value or clear:
        assert type(event).__name__ == "TypeTextEvent"
        assert event.kwargs == {"node": session.get_element_by_index.return_value, "text": value, "clear": clear}
    else:
        assert type(event).__name__ == "ClickElementEvent"
    if submit:
        assert type(events[1]).__name__ == "SendKeysEvent"
        assert events[1].kwargs == {"keys": "Enter"}
    for event in events:
        event.event_result.assert_awaited_once_with(raise_if_any=True, raise_if_none=False)
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["click", "type"])
@pytest.mark.parametrize("failure", ["missing_node", "handler_error"])
async def test_click_type_failures_disconnect(monkeypatch, tmp_home, command, failure):
    cdp, session = _cdp_with_node()
    monkeypatch.setitem(sys.modules, "browser_use.browser.events", _fake_events_module())
    if failure == "missing_node":
        session.get_element_by_index.return_value = None
    else:
        def dispatch(event):
            event.event_result.side_effect = RuntimeError("browser handler failed")
            return event
        session.event_bus.dispatch.side_effect = dispatch
    with patch("cliany_site.browser.axtree.capture_axtree", new=AsyncMock(return_value=_TREE)):
        result = (
            await _run_click(cdp, "2", None) if command == "click"
            else await _run_type(cdp, "2", None, "hello", True, False)
        )
    assert result["ok"] is False
    assert result["error"]["code"] == (
        "E_SELECTOR_NOT_FOUND" if failure == "missing_node" else "E_CDP_UNAVAILABLE"
    )
    assert session.event_bus.dispatch.call_count == (0 if failure == "missing_node" else 1)
    cdp.disconnect.assert_awaited_once()


_TREE = {
    "selector_map": {
        "2": {"ref": "2", "role": "textbox", "name": "Search", "attributes": {}},
        "6": {"ref": "6", "role": "combobox", "name": "Priority", "attributes": {}},
    }
}


@pytest.mark.asyncio
async def test_select_uses_existing_browser_use_select_event(monkeypatch):
    cdp, session = _cdp_with_node()
    monkeypatch.setitem(sys.modules, "browser_use.browser.events", _fake_events_module())

    with patch("cliany_site.browser.axtree.capture_axtree", new=AsyncMock(return_value=_TREE)):
        result = await _run_select(cdp, "6", None, "High")

    assert result["ok"] is True
    assert result["data"]["status"] == "selected"
    event = session.event_bus.dispatch.call_args.args[0]
    assert event.__class__.__name__ == "SelectDropdownOptionEvent"
    assert event.kwargs["text"] == "High"
    cdp.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_focuses_a_semantic_target_then_sends_enter(monkeypatch):
    cdp, session = _cdp_with_node()
    monkeypatch.setitem(sys.modules, "browser_use.browser.events", _fake_events_module())

    with patch("cliany_site.browser.axtree.capture_axtree", new=AsyncMock(return_value=_TREE)):
        result = await _run_submit(cdp, "2", None)

    assert result["ok"] is True
    assert result["data"]["submitted"] is True
    focus_event, submit_event = [call.args[0] for call in session.event_bus.dispatch.call_args_list]
    assert focus_event.__class__.__name__ == "ClickElementEvent"
    assert submit_event.__class__.__name__ == "SendKeysEvent"
    assert submit_event.kwargs["keys"] == "Enter"
    cdp.disconnect.assert_awaited_once()
