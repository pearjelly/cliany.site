from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from contextlib import AsyncExitStack
from typing import Any

from cdp_use import CDPClient

_VISIBLE = """(selector) => {
    const element = document.querySelector(selector);
    if (!element) return {visible: false};
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return {visible: style.visibility !== 'hidden' && style.visibility !== 'collapse'
        && rect.width > 0 && rect.height > 0};
}"""


async def wait_for_current_page(
    browser_session: Any,
    *,
    selector: str | None = None,
    state: str = "networkidle",
    timeout: float = 30.0,
) -> None:
    states = {
        "networkidle": {"networkIdle"},
        "load": {"load", "networkIdle"},
        "domcontentloaded": {"DOMContentLoaded", "load", "networkIdle"},
    }
    if timeout <= 0 or (not selector and state not in states):
        raise ValueError("Invalid page wait condition")
    deadline = time.monotonic() + timeout
    try:
        async with asyncio.timeout(timeout), AsyncExitStack() as stack:
            await _wait(browser_session, selector, states.get(state, set()), deadline, stack)
    except TimeoutError:
        raise
    except Exception as exc:
        raise RuntimeError("Page wait unavailable") from exc


async def _wait(
    browser_session: Any,
    selector: str | None,
    states: set[str],
    deadline: float,
    stack: AsyncExitStack,
) -> None:
    page = await browser_session.get_current_page()
    if page is None:
        raise RuntimeError("Current page unavailable")
    client = None
    session_id = None
    events: deque[dict[str, Any]] = deque(maxlen=50)
    if not selector:
        target = (await page.get_target_info())["targetId"]
        connection = browser_session.cdp_client
        client = await stack.enter_async_context(
            CDPClient(
                connection.url,
                additional_headers=connection.additional_headers,
            )
        )
        session_id = (
            await client.send.Target.attachToTarget(
                params={"targetId": target, "flatten": True},
            )
        )["sessionId"]
        await client.send.Page.enable(session_id=session_id)
        frame_id = (await client.send.Page.getFrameTree(session_id=session_id))["frameTree"]["frame"]["id"]

        def observed(event: Any, session_id: str | None = None) -> None:
            if session_id == attached_session and event.get("frameId") == frame_id:
                events.append(event)

        attached_session = session_id
        # CDP-use has one callback per event; keep this listener off the backend's connection.
        client.register.Page.lifecycleEvent(observed)
        await client.send.Page.setLifecycleEventsEnabled(
            params={"enabled": True},
            session_id=session_id,
        )
    while time.monotonic() < deadline:
        if selector:
            # This is the user's explicit CSS condition, never an action-target fallback.
            visible = await page.evaluate(_VISIBLE, selector)
            if isinstance(visible, str):
                try:
                    visible = json.loads(visible)
                except (ValueError, TypeError):
                    visible = None
            ready = isinstance(visible, dict) and visible.get("visible") is True
        else:
            assert client is not None and session_id is not None
            frame = (
                await client.send.Page.getFrameTree(
                    session_id=session_id,
                )
            )["frameTree"]["frame"]
            loader = frame.get("loaderId")
            ready = bool(loader) and any(
                event.get("loaderId") == loader and event.get("name") in states for event in list(events)
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Page wait timed out")
        if ready:
            return
        await asyncio.sleep(min(0.05, remaining))
    raise TimeoutError("Page wait timed out")
