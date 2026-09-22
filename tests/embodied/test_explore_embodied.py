# pyright: reportMissingImports=false
"""真实 headless Chromium + CDP 的 AXTree 具身测试。"""

import asyncio
import json
import socket
import sys

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
        assert tree["url"] == page_url
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
@pytest.mark.parametrize("command", ["click", "type"])
async def test_browser_cli_changes_real_form(
    local_server, headless_browser_cdp_url, tmp_home, command
):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(
            headless_browser_cdp_url.replace("ws://", "http://")
        )
        page = await browser.contexts[0].new_page()
        await page.goto(f"{local_server}/browser_atoms.html")

        async def run(*args):
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", headless_browser_cdp_url,
                "browser", *args, "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            assert process.returncode == 0, (stdout.decode(), stderr.decode())
            result = json.loads(stdout)
            assert result["ok"] is True, result
            return result

        try:
            if command == "click":
                await run("click", "--text", "Apply")
                assert await page.get_by_role("status").text_content() == "seed"
            else:
                await page.get_by_label("Name").press("End")
                await run("type", "--text", "Name", "--value", "Ada")
                assert await page.get_by_label("Name").input_value() == "seedAda"
                assert await page.get_by_role("status").text_content() == "untouched"
                await run("type", "--text", "Name", "--value", "Grace", "--clear", "--submit")
                assert await page.get_by_label("Name").input_value() == "Grace"
                assert await page.get_by_role("status").text_content() == "Grace"
                await run("type", "--text", "Name", "--value", "", "--submit")
                assert await page.get_by_label("Name").input_value() == "Grace"
                assert await page.get_by_role("status").text_content() == "Grace"
                await run("type", "--text", "Name", "--value", "", "--clear")
                assert await page.get_by_label("Name").input_value() == ""
        finally:
            await browser.close()


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


@pytest.mark.embodied
@pytest.mark.asyncio
@pytest.mark.parametrize("entrypoint", ["sdk", "http", "cli", "workflow", "batch", "explore_cli"])
async def test_generated_adapter_returns_real_form_data(
    local_server, headless_browser_cdp_url, fallback_browser, tmp_home, entrypoint, monkeypatch
):
    from aiohttp.test_utils import TestClient, TestServer

    from cliany_site.codegen.generator import AdapterGenerator, save_adapter
    from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
    from cliany_site.sdk import ClanySite
    from cliany_site.server import APIServer

    url = f"{local_server}/browser_atoms.html"
    actions = [
        ActionStep("type", url, value="{{name}}", target_ref="999998", target_name="Name", target_role="textbox"),
        ActionStep("click", url, target_ref="999999", target_name="Apply", target_role="button"),
        ActionStep("extract", url, selector="output", extract_mode="list", fields_map={"name": ""}),
    ]
    result = ExploreResult(
        pages=[PageInfo(url, "Browser command fixture")], actions=actions,
        commands=[CommandSuggestion("read-name", "Read form result", [{"name": "name", "required": True}], [0, 1, 2])],
    )
    if entrypoint == "explore_cli":
        from types import SimpleNamespace

        from cliany_site.explorer import engine

        observed = []
        capture = engine.capture_axtree

        async def observe(session, *args, **kwargs):
            tree = await capture(session, *args, **kwargs)
            observed.append(tree)
            return tree

        class ScriptedModel:
            model = "offline-form-contract"
            calls = 0

            async def ainvoke(self, prompt):
                self.calls += 1
                assert self.calls == 1
                nodes = observed[-1]["selector_map"]
                name_ref = next(ref for ref, node in nodes.items() if node["name"] == "Name" and node["role"] == "textbox")
                apply_ref = next(ref for ref, node in nodes.items() if node["name"] == "Apply" and node["role"] == "button")
                return SimpleNamespace(content=json.dumps({
                    "actions": [
                        {"type": "type", "ref": name_ref, "value": "Ada"},
                        {"type": "click", "ref": apply_ref},
                        {"type": "extract", "selector": "output", "extract_mode": "list", "fields": {"name": ""}},
                    ],
                    "commands": [{"name": "read-name", "description": "Read form result",
                                  "args": [{"name": "name", "required": True, "action_index": 0}],
                                  "action_steps": [0, 1, 2]}],
                    "done": True,
                }))

        model = ScriptedModel()
        monkeypatch.setattr(engine, "capture_axtree", observe)
        monkeypatch.setattr(engine, "_get_llm", lambda **kwargs: model)
        result = await engine.WorkflowExplorer(cdp_url=headless_browser_cdp_url).explore(
            url, "Enter Ada, apply, and extract the resulting name as a reusable command", record=False,
        )
        assert model.calls == 1
        assert [action.action_type for action in result.actions] == ["type", "click", "extract"]
        assert result.actions[0].target_name == "Name"
        assert result.actions[0].target_role == "textbox"
        assert result.commands[0].name == "read-name"
        assert result.pages[0].url == url
        assert all(action.page_url == url for action in result.actions)
        async with async_playwright() as playwright:
            inspection = await playwright.chromium.connect_over_cdp(headless_browser_cdp_url.replace("ws://", "http://"))
            try:
                page = next(page for ctx in inspection.contexts for page in ctx.pages if page.url == url)
                assert await page.locator("output").inner_text() == "Ada"
            finally:
                await inspection.close()
    save_adapter("127.0.0.1", AdapterGenerator().generate(result, "127.0.0.1"), explore_result=result)
    # Each request uses a fresh SDK/session; it must navigate from metadata itself.
    for name in ("Ada", "Grace"):
        if entrypoint == "sdk":
            async with ClanySite(cdp_url=headless_browser_cdp_url) as sdk:
                response = await sdk.execute("127.0.0.1", "read-name", params={"name": name})
        elif entrypoint == "http":
            server = APIServer(cdp_url=headless_browser_cdp_url)
            async with TestClient(TestServer(server._build_app())) as client:
                http_response = await client.post("/execute", json={
                    "domain": "127.0.0.1", "command": "read-name", "params": {"name": name},
                })
                response = await http_response.json()
                assert http_response.status == 200, response
        else:
            fallback, fallback_url = fallback_browser
            monkeypatch.setenv("CLIANY_CDP_URL", fallback_url)
            command = ["127.0.0.1", "read-name", "--name", name, "--json"]
            if entrypoint == "workflow":
                import yaml

                workflow_file = tmp_home / "workflow.yaml"
                workflow_file.write_text(yaml.safe_dump({
                    "name": "read form", "steps": [{
                        "name": "read", "adapter": "127.0.0.1", "command": "read-name",
                        "params": {"name": name},
                    }],
                }))
                command = ["workflow", "run", str(workflow_file), "--json"]
            elif entrypoint == "batch":
                batch_file = tmp_home / "names.csv"
                batch_file.write_text(f"name\n{name}\n", encoding="utf-8")
                command = ["workflow", "batch", "127.0.0.1", "read-name", str(batch_file), "--json"]
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", headless_browser_cdp_url,
                *command,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            assert all(page.url == "about:blank" for ctx in fallback.contexts for page in ctx.pages)
            response = json.loads(stdout)
            assert process.returncode == 0, (response, stderr.decode())
            if entrypoint in ("workflow", "batch"):
                assert response["success"] is True, response
                key = "steps" if entrypoint == "workflow" else "results"
                response = {"data": response["data"][key][0]["data"]}
            else:
                assert response["ok"] is True, response
            extracts = [r for r in response["data"]["results"] if r["command"] == "browser extract"]
            assert extracts[0]["data"]["content"] == [{"name": name}]
            assert response["data"]["quality"]["ok"] is True
            async with async_playwright() as playwright:
                inspection = await playwright.chromium.connect_over_cdp(headless_browser_cdp_url.replace("ws://", "http://"))
                try:
                    page = next(page for ctx in inspection.contexts for page in ctx.pages if page.url == url)
                    assert await page.locator("output").get_attribute("data-submits") == "1"
                finally:
                    await inspection.close()
            continue
        assert response["success"] is True, response
        assert response["data"]["results"][0]["data"] == [{"name": name}]
        assert response["data"]["quality"]["ok"] is True


@pytest.fixture
async def fallback_browser():
    port = _pick_free_port()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=[f"--remote-debugging-port={port}"])
        await browser.new_page()
        try:
            yield browser, f"ws://127.0.0.1:{port}"
        finally:
            await browser.close()
