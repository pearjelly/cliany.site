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
from cliany_site.explorer import engine
from cliany_site.explorer.engine import WorkflowExplorer
from cliany_site.sdk import ClanySite

playwright = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.mark.embodied
async def test_failed_placeholder_type_on_link_cannot_survive_generation(
    tmp_home, monkeypatch, local_server, unused_tcp_port,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setattr(engine, "get_config", lambda: replace(
        get_config(), explore_max_steps=4, llm_retry_max_attempts=1, vision_enabled=False,
    ))
    snapshots, attempted = [], []
    original_execute = engine.execute_action_steps

    async def capture(session):
        tree = await capture_axtree(session)
        snapshots.append(tree)
        return tree

    async def execute(session, actions, **kwargs):
        result = await original_execute(session, actions, **kwargs)
        attempted.extend(dict(action) for action in actions)
        return result

    monkeypatch.setattr(engine, "capture_axtree", capture)
    monkeypatch.setattr(engine, "execute_action_steps", execute)
    source = local_server + "/unobserved_extract_start.html"
    form = local_server + "/extract_plan_form.html"
    calls, query_index = 0, None

    async def respond(_messages):
        nonlocal calls, query_index
        calls += 1
        tree = snapshots[-1]

        def ref(name, role):
            return next(key for key, value in tree["selector_map"].items()
                        if value.get("name") == name and value.get("role") == role)

        reply = {"done": False}
        if tree["url"] == source:
            target = ref("Full Search", "link")
            reply["actions"] = [{"type": "click", "ref": target}]
            if calls == 1:
                reply["actions"].append({"type": "type", "ref": target, "value": "Ada",
                                         "description": "placeholder"})
        elif query_index is None:
            assert tree["url"] == form
            query_index = len(attempted)
            reply["actions"] = [{"type": "type", "ref": ref("Query", "textbox"), "value": "Ada"},
                                {"type": "click", "ref": ref("Search", "button")}]
        else:
            reply.update(done=True, actions=[{"type": "extract", "selector": "#results li", "extract_mode": "list",
                                              "fields": {"title": "a", "url": "a@href"}}], commands=[{
                "name": "search-docs", "action_steps": list(range(len(attempted) + 1)),
                "args": [{"name": "query", "required": True, "default": "Ada", "action_index": query_index}],
            }])
        return SimpleNamespace(content=json.dumps(reply))

    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr(engine, "_get_llm", lambda **_kwargs: model)
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    domain = f"127.0.0.1_{urlparse(local_server).port}"
    async with playwright.async_playwright() as browser_runtime:
        context = await browser_runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, viewport={"width": 1280, "height": 720},
            env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            result = await WorkflowExplorer(cdp_url=endpoint).explore(source, "Search docs", record=False)
            save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": source}, result)
            directory = runtime / "adapters" / domain
            before = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json")}
            async with ClanySite(cdp_url=endpoint) as sdk:
                verified = await sdk.verify(domain)
                replay = await sdk.execute(domain, "search-docs", params={"query": "Grace"})
            evidence = {"model_calls": calls, "actions": [{"type": action.action_type, "role": action.target_role}
                                                          for action in result.actions],
                        "query_index": query_index, "verified": verified, "replay": replay,
                        "core_unchanged": before == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                                                     for name in before}}
            (tmp_home / "value-target-evidence.json").write_text(json.dumps(evidence, indent=2))
            assert verified["success"] is True
            assert replay["success"] is True, replay
            assert [row for extraction in replay["data"]["results"] for row in extraction.get("data", [])] == [
                {"title": "Grace", "url": "/docs/Grace.html"},
            ]
            assert calls == 4 and query_index == 1 and len(result.actions) == 4
            assert all(action.action_type != "type" or action.target_role != "link" for action in result.actions)
            assert evidence["core_unchanged"] is True
        finally:
            await context.close()
