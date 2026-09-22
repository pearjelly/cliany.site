# pyright: reportMissingImports=false
"""真实 headless Chromium + CDP 的 AXTree 具身测试。"""

import json
import socket

import pytest

playwright_async_api = pytest.importorskip("playwright.async_api")
async_playwright = playwright_async_api.async_playwright


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
async def headless_browser_cdp_url():
    """用 Playwright 启动 headless Chromium，并暴露给 cliany.site 使用的 CDP 端口。"""
    port = _pick_free_port()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[f"--remote-debugging-port={port}"],
        )
        try:
            yield f"ws://127.0.0.1:{port}"
        finally:
            await browser.close()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_capture_axtree_from_headless_chrome(local_server, headless_browser_cdp_url):
    from cliany_site.browser.axtree import capture_axtree
    from cliany_site.browser.cdp import CDPConnection

    page_url = f"{local_server}/sample_form.html"
    cdp = CDPConnection(cdp_url=headless_browser_cdp_url, headless=True)
    browser_session = await cdp.connect()

    try:
        await browser_session.navigate_to(page_url, new_tab=False)

        tree = await capture_axtree(browser_session)
        selector_map = tree["selector_map"]

        search_fields = [
            element
            for element in selector_map.values()
            if element.get("role") in {"input", "textbox", "searchbox"}
            and (
                "search" in str(element.get("name", "")).lower()
                or "搜索" in str(element.get("name", ""))
                or "search" in str(element.get("attributes", {})).lower()
                or "搜索" in str(element.get("attributes", {}))
            )
        ]

        assert search_fields, f"selector_map 应含搜索框元素，实际: {list(selector_map.values())[:10]}"
    finally:
        await cdp.disconnect()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_action_replay_changes_real_page_only_outside_dry_run(
    local_server, headless_browser_cdp_url, tmp_home, monkeypatch
):
    from cliany_site.action_runtime import execute_action_steps
    from cliany_site.browser.cdp import CDPConnection

    monkeypatch.setenv("CLIANY_POST_CLICK_NAV_DELAY", "0")
    cdp = CDPConnection(cdp_url=headless_browser_cdp_url, headless=True)
    session = await cdp.connect()
    try:
        await session.navigate_to(f"{local_server}/action_replay.html", new_tab=False)
        page = await session.get_current_page()
        actions = [
            {"type": "type", "target_name": "Name", "target_role": "textbox", "value": "Ada"},
            {"type": "select", "target_name": "Color", "target_role": "combobox", "value": "Blue"},
            {"type": "click", "target_name": "Apply", "target_role": "button"},
        ]
        state = (
            "() => [document.getElementById('name').value, "
            "document.getElementById('color').value, document.getElementById('result').textContent]"
        )
        await execute_action_steps(session, actions, dry_run=True)
        assert json.loads(await page.evaluate(state)) == ["", "Red", "untouched"]
        await execute_action_steps(session, actions)
        assert json.loads(await page.evaluate(state)) == ["Ada", "Blue", "Ada:Blue"]
    finally:
        await cdp.disconnect()
