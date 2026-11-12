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
@pytest.mark.parametrize("publish", [True, False])
async def test_submit_then_extract_requires_fresh_observed_rows(
    local_server, tmp_home, monkeypatch, unused_tcp_port, publish,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_CAPTURE_NETWORK", "0")
    monkeypatch.setenv("CLIANY_CAPTURE_CONSOLE", "0")
    monkeypatch.setattr(engine, "get_config", lambda: replace(
        get_config(), explore_max_steps=2, llm_retry_max_attempts=1, vision_enabled=False,
    ))
    monkeypatch.setattr(engine, "_EXTRACT_GROUNDING_TIMEOUT_SECONDS", 2.0)
    snapshots = []
    prompts = []
    extracted = []
    execute = engine.execute_action_steps
    url = f"{local_server}/late_submit_collection.html"
    result_url = url + "?query=sample"
    extract = {"type": "extract", "selector": "#results li", "extract_mode": "list",
               "fields": {"title": "a", "url": "a@href"}}

    async def observe(session, **kwargs):
        tree = await capture_axtree(session, **kwargs)
        snapshots.append(tree)
        return tree

    monkeypatch.setattr(engine, "capture_axtree", observe)

    async def dispatch(session, actions, **kwargs):
        await execute(session, actions, **kwargs)
        extracted.extend(kwargs["extraction_results"])

    monkeypatch.setattr(engine, "execute_action_steps", dispatch)

    async with playwright.async_playwright() as runtime_browser:
        context = await runtime_browser.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"],
        )

        async def plan(prompt):
            prompts.append(prompt)
            tree = snapshots[-1]
            if len(prompts) == 1:
                ref = next(ref for ref, node in tree["selector_map"].items()
                           if node["role"] == "button" and node["name"] == "Search")
                response = {"actions": [{"type": "click", "ref": ref}], "done": False}
            else:
                assert len(prompts) == 2 and tree["url"] == result_url
                assert tree["extract_candidates"]
                assert engine._invalid_extract_targets([extract], tree) == [{"action_index": 0}]
                if publish:
                    page = next(page for page in context.pages if page.url == result_url)
                    await page.evaluate("() => { setTimeout(publishResults, 150); }")
                response = {"actions": [extract], "done": True, "commands": [
                    {"name": "read-results", "description": "Read results", "args": [], "action_steps": [0, 1]},
                ]}
            return SimpleNamespace(content=json.dumps(response))

        model = SimpleNamespace(model="offline-control", ainvoke=plan)
        monkeypatch.setattr(engine, "_get_llm", lambda **_kwargs: model)
        explorer = engine.WorkflowExplorer(cdp_url=f"http://127.0.0.1:{unused_tcp_port}")
        try:
            if publish:
                result = await explorer.explore(url, "Submit the form and read the resulting items", record=True)
                assert [action.action_type for action in result.actions] == ["click", "extract"]
                assert result.actions[1].extract_target
                assert result.commands[0].action_steps == [0, 1]
                assert len(extracted) == 1
                assert [row["title"] for row in extracted[0]["data"]] == ["Observed result"]
                assert extracted[0]["data"][0]["url"].endswith("/index.html")
            else:
                with pytest.raises(ExploreContractError) as error:
                    await explorer.explore(url, "Submit the form and read the resulting items", record=True)
                assert error.value.reason == "extract_selector_ungrounded"
                journal, = runtime.glob("recordings/*/*/failure.json")
                failure = json.loads(journal.read_text())
                assert failure["dispatch_status"] == "not_started" and failure["execution_receipt"] is False
                assert failure["actions_before_count"] == 1
                assert extracted == []
            assert len(prompts) == 2
        finally:
            await context.close()
