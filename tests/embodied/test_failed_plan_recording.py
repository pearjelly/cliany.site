import json
import os
import stat
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer import engine

playwright = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.mark.embodied
@pytest.mark.parametrize("record", [True, False])
async def test_native_rejected_plan_retains_only_private_failure_evidence(
    tmp_home, monkeypatch, local_server, unused_tcp_port, record,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_CAPTURE_NETWORK", "0")
    monkeypatch.setenv("CLIANY_CAPTURE_CONSOLE", "0")
    monkeypatch.setattr(engine, "get_config", lambda: replace(
        get_config(), explore_max_steps=1, llm_retry_max_attempts=1, vision_enabled=False,
    ))
    observations = []

    async def capture(session):
        tree = await capture_axtree(session)
        observations.append(tree)
        return tree

    monkeypatch.setattr(engine, "capture_axtree", capture)
    plan = {"actions": [{"type": "extract", "selector": "#unobserved li", "extract_mode": "list"}], "done": False}
    model = SimpleNamespace(model="offline-control", ainvoke=AsyncMock(
        return_value=SimpleNamespace(content=json.dumps(plan)),
    ))
    monkeypatch.setattr(engine, "_get_llm", lambda **_kwargs: model)
    dispatch = AsyncMock()
    monkeypatch.setattr(engine, "execute_action_steps", dispatch)
    url = local_server + "/extract_plan_form.html"
    async with playwright.async_playwright() as browser_runtime:
        context = await browser_runtime.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            with pytest.raises(ExploreContractError) as error:
                await engine.WorkflowExplorer(cdp_url=f"http://127.0.0.1:{unused_tcp_port}").explore(
                    url, "Controlled rejected extraction", record=record,
                )
            assert error.value.reason == "extract_selector_ungrounded"
            dispatch.assert_not_awaited()
            assert len(observations) == model.ainvoke.await_count == 1
            assert not list(runtime.glob("adapters/*/commands.py"))
            files = list(runtime.glob("recordings/*/*/failure.json"))
            if record:
                assert len(files) == 1
                data = json.loads(files[0].read_text())
                assert data["reason"] == error.value.reason and data["phase"] == "planning"
                assert data["dispatch_status"] == "not_started" and data["execution_receipt"] is False
                assert json.loads(data["llm_response_raw"]) == plan
                assert data["planning_axtree"]["url"] == url and "screenshot" not in data["planning_axtree"]
                assert stat.S_IMODE(files[0].stat().st_mode) == 0o600
                manifest = json.loads(files[0].with_name("manifest.json").read_text())
                assert manifest["steps"] == [] and manifest["completed"] is False
            else:
                assert not files and not (runtime / "recordings").exists()
        finally:
            await context.close()
