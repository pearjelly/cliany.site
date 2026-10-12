import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

playwright = pytest.importorskip("playwright.async_api")


@pytest.mark.embodied
async def test_ambiguous_plan_changes_to_unique_observed_route_before_execution(tmp_home, monkeypatch):
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
    domain = "semantic-plan.example.test"
    url = f"http://{domain}/semantic_plan_home.html"
    snapshots = []

    async def capture(session):
        tree = await capture_axtree(session)
        snapshots.append(tree)
        return tree

    monkeypatch.setattr("cliany_site.explorer.engine.capture_axtree", capture)
    async with playwright.async_playwright() as runtime:
        import socket

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        context = await runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, viewport={"width": 1280, "height": 720},
            args=[f"--remote-debugging-port={port}"],
        )
        calls = 0
        pages = Path(__file__).parent / "pages"

        async def serve(route):
            path = Path(route.request.url.split("/")[-1])
            await route.fulfill(status=200, content_type="text/html", body=(pages / path).read_text())

        await context.route(f"http://{domain}/**", serve)

        def ref(name, role):
            return next(key for key, value in snapshots[-1]["selector_map"].items()
                        if value.get("name") == name and value.get("role") == role)

        async def respond(_messages):
            nonlocal calls
            calls += 1
            if calls == 1:
                reply = {"actions": [{"type": "type", "ref": ref("Quick search", "searchbox"),
                                      "value": "DO-NOT-WRITE"}], "commands": [], "done": False}
            elif calls == 2:
                page = next(page for page in context.pages if page.url == url)
                inputs = await page.get_by_role("searchbox", name="Quick search", exact=True).all()
                assert [await field.input_value() for field in inputs] == ["", ""]
                reply = {"actions": [{"type": "click", "ref": ref("Full Search", "link")}],
                         "commands": [], "done": False}
            else:
                assert calls == 3
                reply = {"actions": [
                    {"type": "type", "ref": ref("Query", "textbox"), "value": "Ada"},
                    {"type": "click", "ref": ref("Search", "button")},
                    {"type": "extract", "selector": "#results li", "extract_mode": "list", "fields": {"name": "span"}},
                ], "done": True, "commands": [{"name": "search-values", "description": "Search values",
                    "args": [{"name": "query", "required": True, "default": "Ada", "action_index": 1}],
                    "action_steps": [0, 1, 2, 3], "expects_nonempty": True}]}
            return SimpleNamespace(content=json.dumps(reply))

        model = SimpleNamespace(model="deterministic-fixture", ainvoke=AsyncMock(side_effect=respond))
        monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
        endpoint = f"http://127.0.0.1:{port}"
        try:
            result = await WorkflowExplorer(cdp_url=endpoint).explore(url, "Search names", record=False)
            assert model.ainvoke.await_count == 3
            assert len(result.actions) == 4 and result.actions[0].target_name == "Full Search"
            assert all(action.value != "DO-NOT-WRITE" for action in result.actions)
            code = AdapterGenerator().generate(result, domain)
            save_adapter(domain, code, {"source_url": url}, result)
            async with ClanySite(cdp_url=endpoint) as sdk:
                assert (await sdk.verify(domain))["success"] is True
                replay = await sdk.execute(domain, "search-values", params={"query": "Grace"})
                assert replay["success"] is True, replay
                rows = [row for extraction in replay["data"]["results"] for row in extraction.get("data", [])]
                assert rows == [{"name": "Grace"}]
                page = next(page for page in context.pages if page.url.endswith("/semantic_plan_form.html"))
                assert await page.get_by_role("list", name="Matches").inner_text() == "Grace"
        finally:
            await context.close()
