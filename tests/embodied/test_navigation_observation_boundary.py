import json
import os
from dataclasses import replace
from types import SimpleNamespace

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer import engine

playwright = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.mark.embodied
@pytest.mark.parametrize("repair", [True, False])
async def test_distinct_cross_page_clicks_require_a_new_observation(
    local_server, tmp_home, monkeypatch, unused_tcp_port, repair,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_CAPTURE_NETWORK", "0")
    monkeypatch.setenv("CLIANY_CAPTURE_CONSOLE", "0")
    monkeypatch.setattr(engine, "get_config", lambda: replace(
        get_config(), explore_max_steps=3 if repair else 5, llm_retry_max_attempts=1, vision_enabled=False,
    ))
    observations = []
    prompts = []
    dispatches = []
    execute = engine.execute_action_steps
    origin = f"{local_server}/distinct_navigation_links.html"
    destination = f"{local_server}/extract_plan_form.html"
    fallback = f"{local_server}/late_submit_collection.html"

    async def observe(session, **kwargs):
        tree = await capture_axtree(session, **kwargs)
        observations.append(tree)
        return tree

    async def dispatch(session, actions, **kwargs):
        dispatches.append([action["type"] for action in actions])
        await execute(session, actions, **kwargs)

    monkeypatch.setattr(engine, "capture_axtree", observe)
    monkeypatch.setattr(engine, "execute_action_steps", dispatch)

    async def plan(prompt):
        prompts.append(prompt)
        tree = observations[-1]
        refs = {node["name"]: ref for ref, node in tree["selector_map"].items()}
        if len(prompts) < 3:
            assert tree["url"] == origin
            assert not dispatches
            clicks = [{"type": "click", "ref": refs["Search page"]}]
            if len(prompts) == 1 or not repair:
                clicks.append({"type": "click", "ref": refs["Complete table of contents"],
                               "description": "Fallback only, do not execute"})
            response = {"actions": clicks, "done": False}
        else:
            assert tree["url"] == destination and "Complete table of contents" not in refs
            assert dispatches == [["click"]]
            response = {
                "actions": [{"type": "type", "ref": refs["Query"], "value": "sample"}],
                "done": True,
                "commands": [{"name": "open-search-and-type", "description": "Enter a query", "args": [],
                              "action_steps": [0, 1]}],
            }
        return SimpleNamespace(content=json.dumps(response))

    monkeypatch.setattr(engine, "_get_llm", lambda **_kwargs: SimpleNamespace(model="offline-control", ainvoke=plan))
    async with playwright.async_playwright() as browser_runtime:
        context = await browser_runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        visited = []
        context.on("request", lambda request: visited.append(request.url) if request.is_navigation_request() else None)
        explorer = engine.WorkflowExplorer(cdp_url=f"http://127.0.0.1:{unused_tcp_port}")
        try:
            if repair:
                result = await explorer.explore(origin, "Open Search page and enter sample", record=True)
                assert dispatches == [["click"], ["type"]]
                assert [action.action_type for action in result.actions] == ["click", "type"]
                assert result.commands[0].action_steps == [0, 1]
                page = next(page for page in context.pages if page.url == destination)
                assert await page.get_by_role("textbox", name="Query").input_value() == "sample"
                assert len(prompts) == 3 and destination in visited
                assert not list(runtime.glob("recordings/*/*/failure.json"))
            else:
                with pytest.raises(ExploreContractError) as error:
                    await explorer.explore(origin, "Open Search page and enter sample", record=True)
                assert error.value.reason == "navigation_followup_unobserved"
                assert dispatches == [] and len(prompts) == 2 and destination not in visited
                journal, = runtime.glob("recordings/*/*/failure.json")
                failure = json.loads(journal.read_text())
                assert failure["phase"] == "planning" and failure["dispatch_status"] == "not_started"
                assert failure["execution_receipt"] is False and failure["actions_before_count"] == 0
                manifest = json.loads(journal.with_name("manifest.json").read_text())
                assert manifest["steps"] == [] and manifest["completed"] is False
            assert fallback not in visited
        finally:
            await context.close()
