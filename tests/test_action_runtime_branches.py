from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest

from cliany_site.action_runtime import _attempt_adaptive_repair, _resolve_action_node, execute_action_steps


class _AwaitableEvent:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.event_result = mock.AsyncMock(return_value=None)

    def __await__(self):
        async def _wait():
            return self

        return _wait().__await__()


def _event_class(name: str):
    event_cls = type(name, (_AwaitableEvent,), {})
    return event_cls


def _fake_events_module():
    module = ModuleType("browser_use.browser.events")
    module.ClickElementEvent = _event_class("ClickElementEvent")
    module.NavigateToUrlEvent = _event_class("NavigateToUrlEvent")
    module.SelectDropdownOptionEvent = _event_class("SelectDropdownOptionEvent")
    module.SendKeysEvent = _event_class("SendKeysEvent")
    module.TypeTextEvent = _event_class("TypeTextEvent")
    return module


def _browser_session(current_url: str = "https://example.com/page"):
    session = mock.AsyncMock()
    session.get_current_page_url = mock.AsyncMock(return_value=current_url)
    session.event_bus = SimpleNamespace(dispatch=mock.Mock(return_value=_AwaitableEvent()))
    return session


@pytest.mark.asyncio
async def test_resolve_action_node_retries_on_stale_ref():
    session = _browser_session()
    resolved_node = object()
    session.get_element_by_index = mock.AsyncMock(return_value=resolved_node)
    action = {
        "ref": "ref_7",
        "target_name": "提交",
        "target_role": "button",
        "target_attributes": {"id": "submit"},
    }
    stale_tree = {
        "url": "https://example.com/page",
        "selector_map": {
            "7": {"name": "取消", "role": "link", "attributes": {"id": "cancel"}},
        },
    }
    fresh_tree = {
        "url": "https://example.com/page",
        "selector_map": {
            "7": {"name": "提交", "role": "button", "attributes": {"id": "submit"}},
        },
    }

    with mock.patch("cliany_site.action_runtime.capture_axtree", new=mock.AsyncMock(side_effect=[stale_tree, fresh_tree])) as capture:
        with mock.patch("cliany_site.action_runtime._get_resolve_max_retries", return_value=1):
            with mock.patch("cliany_site.action_runtime._get_resolve_retry_delay", return_value=0):
                with mock.patch("cliany_site.action_runtime.asyncio.sleep", new=mock.AsyncMock()) as sleep:
                    result = await _resolve_action_node(session, action)

    assert result is resolved_node
    assert capture.await_count == 2
    sleep.assert_awaited_once_with(0)
    session.get_element_by_index.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_attempt_adaptive_repair_falls_back_to_text():
    session = _browser_session()
    text_match_node = object()
    session.get_element_by_index = mock.AsyncMock(side_effect=[RuntimeError("stale css candidate"), text_match_node])
    fake_llm = SimpleNamespace(ainvoke=mock.AsyncMock(return_value=SimpleNamespace(content='{"selectors": ["ref_3", "ref_8"]}')))
    parse_response = mock.Mock(return_value={"selectors": ["ref_3", "ref_8"]})
    tree = {
        "url": "https://example.com/page",
        "title": "Example",
        "selector_map": {
            "3": {"name": "旧 CSS 候选", "role": "button", "attributes": {}},
            "8": {"name": "按文本命中的候选", "role": "button", "attributes": {}},
        },
    }

    with mock.patch("cliany_site.explorer.engine._get_replay_llm", return_value=fake_llm):
        with mock.patch("cliany_site.explorer.engine._parse_llm_response", parse_response):
            with mock.patch("cliany_site.explorer.engine._to_text", str):
                with mock.patch("cliany_site.action_runtime.capture_axtree", new=mock.AsyncMock(return_value=tree)):
                    with mock.patch("cliany_site.action_runtime.serialize_axtree", return_value="ref_3 ref_8"):
                        with mock.patch("cliany_site.repair_prompts.REPAIR_PROMPT_TEMPLATE", "refs={attempted_refs}"):
                            with mock.patch("cliany_site.action_runtime._get_adaptive_repair_max_attempts", return_value=1):
                                node = await _attempt_adaptive_repair(
                                    session, {"ref": "ref_1", "type": "click", "description": "点击按钮"}
                                )

    assert node is text_match_node
    session.get_element_by_index.assert_has_awaits([mock.call(3), mock.call(8)])
    fake_llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_attempt_vision_locate_called_when_repair_fails():
    session = _browser_session()
    vision_node = object()

    with mock.patch("cliany_site.action_runtime.capture_axtree", new=mock.AsyncMock(return_value={"url": "", "selector_map": {}})):
        with mock.patch("cliany_site.action_runtime._get_resolve_max_retries", return_value=0):
            with mock.patch("cliany_site.action_runtime._adaptive_repair_enabled", return_value=True):
                with mock.patch("cliany_site.action_runtime._attempt_adaptive_repair", new=mock.AsyncMock(return_value=None)) as repair:
                    with mock.patch("cliany_site.action_runtime._attempt_vision_locate", new=mock.AsyncMock(return_value=vision_node)) as vision:
                        result = await _resolve_action_node(session, {"ref": "ref_404", "type": "click"})

    assert result is vision_node
    repair.assert_awaited_once()
    vision.assert_awaited_once()


@pytest.mark.parametrize("action_type", ["click", "type", "select", "navigate", "submit"])
@pytest.mark.asyncio
async def test_route_action_dispatches_by_type(action_type, monkeypatch):
    session = _browser_session()
    events_module = _fake_events_module()
    monkeypatch.setitem(__import__("sys").modules, "browser_use.browser.events", events_module)
    expected_event = {
        "click": "ClickElementEvent",
        "type": "TypeTextEvent",
        "select": "SelectDropdownOptionEvent",
        "navigate": "NavigateToUrlEvent",
        "submit": "ClickElementEvent",
    }[action_type]
    action = {
        "type": action_type,
        "description": f"{action_type} step",
        "ref": "ref_1",
        "url": "https://example.com/next",
        "value": "输入值",
    }

    with mock.patch("cliany_site.action_runtime._resolve_action_node", new=mock.AsyncMock(return_value=object())):
        with mock.patch("cliany_site.action_runtime.asyncio.sleep", new=mock.AsyncMock()):
            with mock.patch("cliany_site.report.save_report"):
                with mock.patch("cliany_site.report.save_execution_log"):
                    await execute_action_steps(session, [action], dry_run=True)

    dispatched_event = session.event_bus.dispatch.call_args.args[0]
    assert dispatched_event.__class__.__name__ == expected_event


@pytest.mark.asyncio
async def test_route_action_unknown_type_raises(monkeypatch):
    session = _browser_session()
    monkeypatch.setitem(__import__("sys").modules, "browser_use.browser.events", _fake_events_module())

    await execute_action_steps(session, [{"type": "hover", "description": "未知动作"}], continue_on_error=False)

    session.event_bus.dispatch.assert_not_called()
