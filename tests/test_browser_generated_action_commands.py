from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cliany_site.commands.browser.select_cmd import _run_select
from cliany_site.commands.browser.submit_cmd import _run_submit


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
