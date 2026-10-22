import hashlib
import json
import os
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import urlparse

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.config import get_config
from cliany_site.explorer.engine import WorkflowExplorer
from cliany_site.sdk import ClanySite

playwright = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.mark.embodied
@pytest.mark.parametrize("condition", ["pure", "mixed", "empty"])
async def test_prompt_does_not_offer_class_only_collection_after_shared_repair(
    tmp_home, monkeypatch, local_server, unused_tcp_port, condition,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime_home = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime_home))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    cfg = replace(get_config(), explore_max_steps=4, llm_retry_max_attempts=1, vision_enabled=False)
    monkeypatch.setattr("cliany_site.explorer.engine.get_config", lambda: cfg)
    snapshots = []

    async def capture(session):
        tree = await capture_axtree(session)
        if condition == "empty" and not snapshots:
            tree = {"url": tree["url"], "element_tree": "", "selector_map": {}, "extract_candidates": []}
        snapshots.append(tree)
        return tree

    monkeypatch.setattr("cliany_site.explorer.engine.capture_axtree", capture)
    calls = 0

    async def respond(messages):
        nonlocal calls
        calls += 1
        assert snapshots[-1]["selector_map"], "Do not plan from the injected empty AX observation"
        if calls == 2:
            def ref(name, role):
                return next(key for key, value in snapshots[-1]["selector_map"].items()
                            if value.get("name") == name and value.get("role") == role)
            reply = {"actions": [{"type": "type", "ref": ref("Query", "textbox"), "value": "Ada"},
                                  {"type": "click", "ref": ref("Search", "button")}], "done": False}
        else:
            assert calls in (1, 3)
            bad_offered = "→ ul.search" in str(messages)
            selector = "ul.search li" if calls == 1 or bad_offered else "#results li"
            reply = {"actions": [{"type": "extract", "selector": selector, "extract_mode": "list",
                                  "fields": {"title": "a", "url": "a@href"}}], "done": calls == 3}
            if calls == 1 and condition == "mixed":
                reply["actions"].insert(0, {"type": "navigate", "url": url})
            if calls == 3:
                reply["commands"] = [{"name": "search-docs", "action_steps": [0, 1, 2],
                                      "args": [{"name": "query", "required": True,
                                                "default": "Ada", "action_index": 0}]}]
        return SimpleNamespace(content=json.dumps(reply))

    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    domain = f"127.0.0.1_{urlparse(local_server).port}"
    url = local_server + "/extract_plan_form.html"
    async with playwright.async_playwright() as browser_runtime:
        context = await browser_runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, viewport={"width": 1280, "height": 720},
            env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            result = await WorkflowExplorer(cdp_url=endpoint).explore(url, "Search docs", record=False)
            assert calls == 3 and len(result.actions) == 3
            assert result.actions[-1].selector == "#results li"
            assert result.actions[-1].extract_target["attributes"] == {"id": "results"}
            save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": url}, result)
            directory = runtime_home / "adapters" / domain
            before = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json")}
            async with ClanySite(cdp_url=endpoint) as sdk:
                assert (await sdk.verify(domain))["success"] is True
                replay = await sdk.execute(domain, "search-docs", params={"query": "Grace"})
                assert replay["success"] is True, replay
                rows = [row for extraction in replay["data"]["results"] for row in extraction.get("data", [])]
                assert rows == [{"title": "Grace", "url": "/docs/Grace.html"}]
                page = next(page for page in context.pages if page.url == url)
                assert await page.locator("#results a").inner_text() == "Grace"
            assert before == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in before}
        finally:
            await context.close()
