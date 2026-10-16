import asyncio
import hashlib
import json
import os
import sys
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlparse

import pytest
from aiohttp.test_utils import TestClient, TestServer

from cliany_site.browser.selector import ground_extract_target
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.sdk import ClanySite
from cliany_site.server import APIServer

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.fixture
def staged_search():
    html = b"""<!doctype html><html><body>
    <h1>Read-only staged search</h1><p id=stage>Group 0</p>
    <button onclick="advance()">Continue</button>
    <button onclick="advance()">Next group</button>
    <form onsubmit="event.preventDefault();render(document.querySelector('input').value)">
      <input aria-label="Search"><button>Search</button>
    </form><ul id=results aria-label="Results"></ul>
    <script>
    let group=0;
    function render(query) {
      const list=document.getElementById('results'); list.replaceChildren();
      if(query==='no-match') return;
      for(const suffix of ['toolkit','helper','extra']) {
        const li=document.createElement('li'); const span=document.createElement('span');
        span.textContent=group+':'+query+':'+suffix; li.append(span); list.append(li);
      }
    }
    function advance() {
      group++; document.getElementById('stage').textContent='Group '+group;
      document.querySelector('input').value=''; render('Preview');
    }
    render('Preview');
    </script></body></html>"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/search"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.embodied
@pytest.mark.parametrize("scenario", ["wizard", "baseline", "repeat"])
async def test_generated_cli_sdk_http_preserve_recorded_workflow(
    scenario, tmp_home, clean_env, no_llm, monkeypatch, staged_search, unused_tcp_port,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    url = staged_search
    domain = f"127.0.0.1_{urlparse(url).port}"
    semantic = {"role": "list", "name": "Results", "attributes": {"id": "results"}}
    candidates = [{"role": "list", "name": "Results", "semantic_name": "Results", "selectors": ["#results"],
                   "root_selector": "#results", "anchor_attributes": {"id": "results"}}]
    target = ground_extract_target("#results li", {"1": semantic}, candidates)
    assert target is not None
    read = ActionStep("extract", url, selector="#results li", extract_mode="list",
                      fields_map={"name": "span"}, extract_target=target)
    field = ActionStep("type", url, target_ref="999", target_name="Search", target_role="textbox", value="Alpha")
    search = ActionStep("click", url, target_ref="998", target_name="Search", target_role="button")
    if scenario == "wizard":
        advance = ActionStep("click", url, target_ref="997", target_name="Continue", target_role="button")
        actions = [advance, replace(advance), field, search, read]
        arg = {"name": "query", "required": True, "action_index": 2, "default": "Alpha"}
    else:
        actions = [field, search, replace(read, purpose="baseline" if scenario == "baseline" else "workflow"),
                   ActionStep("click", url, target_ref="997", target_name="Next group", target_role="button"),
                   replace(field), replace(search), replace(read)]
        binding = {"action_index": 4} if scenario == "baseline" else {"action_indices": [0, 4]}
        arg = {"name": "query", "required": True, "default": "Alpha", **binding}
    result = ExploreResult(pages=[PageInfo(url, "Staged search")], actions=actions, commands=[
        CommandSuggestion("search-groups", "Read requested groups", [arg], list(range(len(actions))), False)])
    save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": url}, result)
    directory = tmp_home / "runtime" / "adapters" / domain
    core = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("commands.py", "metadata.json", "manifest.json") if (directory / name).is_file()}
    metadata = json.loads((directory / "metadata.json").read_text())
    assert len(metadata["commands"][0]["actions"]) == len(actions)

    async def verify(phase):
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "cliany_site", "verify", domain, "--strict", "--json",
            cwd=tmp_home, env=os.environ.copy(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 30)
        except TimeoutError:
            process.kill()
            await process.communicate()
            raise
        (tmp_home / f"{scenario}-strict-{phase}.json").write_bytes(stdout)
        (tmp_home / f"{scenario}-strict-{phase}.stderr.log").write_bytes(stderr)
        payload = json.loads(stdout)
        assert process.returncode == 0 and payload["ok"] is True, payload

    await verify("before")
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    observations = []
    async with playwright_api.async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, args=[f"--remote-debugging-port={unused_tcp_port}"],
            env={**os.environ, **BROWSER_HOME}, viewport={"width": 1280, "height": 900},
        )
        normal = await playwright.chromium.launch(headless=True, env={**os.environ, **BROWSER_HOME})
        client = None
        try:
            page = await normal.new_page()
            async with ClanySite(cdp_url=endpoint) as sdk:
                api = APIServer()
                api._sdk = sdk
                client = TestClient(TestServer(api._build_app()))
                await client.start_server()
                for query in ("Gamma", "no-match"):
                    await page.goto(url)
                    expected = []

                    async def search_page(value):
                        await page.get_by_role("textbox", name="Search", exact=True).fill(value)
                        await page.get_by_role("button", name="Search", exact=True).click()
                        return [{"name": text} for text in await page.locator("#results li span").all_text_contents()]

                    if scenario == "wizard":
                        for _ in range(2):
                            await page.get_by_role("button", name="Continue", exact=True).click()
                    else:
                        expected.append(await search_page("Alpha" if scenario == "baseline" else query))
                        await page.get_by_role("button", name="Next group", exact=True).click()
                    expected.append(await search_page(query))
                    process = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "cliany_site", "--cdp-url", endpoint, domain, "search-groups",
                        "--query", query, "--json", cwd=tmp_home, env=os.environ.copy(),
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                    )
                    try:
                        stdout, _stderr = await asyncio.wait_for(process.communicate(), 60)
                    except TimeoutError:
                        process.kill()
                        await process.communicate()
                        raise
                    cli = json.loads(stdout)
                    (tmp_home / f"{scenario}-{query}-cli.json").write_bytes(stdout)
                    sdk_result = await sdk.execute(domain, "search-groups", params={"query": query})
                    response = await client.post("/execute", json={
                        "domain": domain, "command": "search-groups", "params": {"query": query},
                    })
                    http = await response.json()
                    returned = {
                        "cli": [step["data"]["content"] for step in cli.get("data", {}).get("results", [])
                                if step.get("command") == "browser extract"],
                        "sdk": [step["data"] for step in sdk_result.get("data", {}).get("results", [])
                                if "data" in step],
                        "http": [step["data"] for step in http.get("data", {}).get("results", []) if "data" in step],
                    }
                    observations.append({"query": query, "expected": expected, "returned": returned,
                                         "cli": cli, "sdk": sdk_result, "http": http,
                                         "exit_code": process.returncode, "http_status": response.status})
                    (tmp_home / f"{scenario}-evidence.json").write_text(json.dumps(observations, indent=2))
            assert all(row["exit_code"] == 0 and row["cli"].get("ok") is True
                       and row["sdk"].get("success") is True and row["http"].get("success") is True
                       and row["http_status"] == 200
                       and all(actual == row["expected"] for actual in row["returned"].values())
                       for row in observations), observations
            await verify("after")
            assert core == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in core}
        finally:
            if client is not None:
                await client.close()
            await normal.close()
            await context.close()
