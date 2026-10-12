import json
import os
import socket
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

playwright = pytest.importorskip("playwright.async_api")


@pytest.mark.embodied
async def test_extract_plan_rejects_class_only_identity_and_replays_changed_input(tmp_home, monkeypatch):
    import pwd

    from cliany_site.browser.axtree import capture_axtree
    from cliany_site.codegen.generator import AdapterGenerator, save_adapter
    from cliany_site.config import get_config, reset_config
    from cliany_site.explorer.engine import WorkflowExplorer
    from cliany_site.sdk import ClanySite

    monkeypatch.setenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / ".cliany-site"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    reset_config()
    cfg = replace(get_config(), explore_max_steps=4, llm_retry_max_attempts=1, vision_enabled=False)
    monkeypatch.setattr("cliany_site.explorer.engine.get_config", lambda: cfg)
    snapshots = []

    async def capture(session):
        tree = await capture_axtree(session)
        snapshots.append(tree)
        return tree

    monkeypatch.setattr("cliany_site.explorer.engine.capture_axtree", capture)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    domain = "extract-plan.example.test"
    url = f"http://{domain}/extract_plan_form.html"
    calls = 0

    async def respond(_messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            def ref(name, role):
                return next(key for key, value in snapshots[-1]["selector_map"].items()
                            if value.get("name") == name and value.get("role") == role)
            reply = {"actions": [{"type": "type", "ref": ref("Query", "textbox"), "value": "Ada"},
                                  {"type": "click", "ref": ref("Search", "button")}], "done": False}
        else:
            assert calls in (2, 3)
            reply = {"actions": [{"type": "extract", "selector": "ul.search li" if calls == 2 else "#results li",
                                  "extract_mode": "list", "fields": {"title": "a", "url": "a@href"}}],
                     "done": True, "commands": [{"name": "search-docs", "action_steps": [0, 1, 2],
                        "args": [{"name": "query", "required": True, "default": "Ada", "action_index": 0}]}]}
        return SimpleNamespace(content=json.dumps(reply))

    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
    async with playwright.async_playwright() as runtime:
        context = await runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, viewport={"width": 1280, "height": 720},
            args=[f"--remote-debugging-port={port}"],
        )
        html = (Path(__file__).parent / "pages/extract_plan_form.html").read_text()
        await context.route(
            f"http://{domain}/**", lambda route: route.fulfill(status=200, content_type="text/html", body=html),
        )
        endpoint = f"http://127.0.0.1:{port}"
        try:
            result = await WorkflowExplorer(cdp_url=endpoint).explore(url, "Search docs", record=False)
            assert calls == 3
            assert len(result.actions) == 3 and result.commands[0].action_steps == [0, 1, 2]
            assert result.actions[-1].selector == "#results li"
            assert result.actions[-1].extract_target["attributes"] == {"id": "results"}
            save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": url}, result)
            async with ClanySite(cdp_url=endpoint) as sdk:
                assert (await sdk.verify(domain))["success"] is True
                replay = await sdk.execute(domain, "search-docs", params={"query": "Grace"})
                assert replay["success"] is True, replay
                rows = [row for extraction in replay["data"]["results"] for row in extraction.get("data", [])]
                assert rows == [{"title": "Grace", "url": "/docs/Grace.html"}]
                page = next(page for page in context.pages if page.url == url)
                assert await page.locator("#results a").inner_text() == "Grace"
        finally:
            await context.close()
