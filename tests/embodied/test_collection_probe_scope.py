import asyncio
import hashlib
import json
import os
import sys
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urljoin, urlparse

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.config import get_config
from cliany_site.errors import ExploreContractError
from cliany_site.explorer.engine import WorkflowExplorer

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.fixture
def scope_search():
    html = """<!doctype html><html><body>
    <a href="?q=Alpha">Alpha results</a>
    <form onsubmit="search(event)"><input aria-label="Search"><button>Search</button></form>
    <ul id=results aria-label="Results"></ul>
    <script>
    function render(query) {
      const list=document.getElementById('results'); list.replaceChildren();
      if (query==='no-match') return;
      for (const suffix of ['toolkit','helper','extra']) {
        const li=document.createElement('li'); const span=document.createElement('span');
        span.textContent=query+' '+suffix; li.append(span); list.append(li);
      }
    }
    function search(event) {
      event.preventDefault(); const query=document.querySelector('input').value;
      history.replaceState(null,'','?q='+encodeURIComponent(query)); render(query);
    }
    render(__QUERY__);
    </script></body></html>"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query).get("q", ["Preview"])[0]
            body = html.replace("__QUERY__", json.dumps(query)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

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
@pytest.mark.parametrize("first_purpose", [None, "probe", "baseline"], ids=["unmarked", "probe", "baseline"])
async def test_collection_scope_preserves_history_and_changed_query_outputs(
    first_purpose, tmp_home, clean_env, no_llm, monkeypatch, scope_search, unused_tcp_port,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    home = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(home))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    cfg = replace(get_config(), explore_max_steps=4, llm_retry_max_attempts=1, vision_enabled=False)
    monkeypatch.setattr("cliany_site.explorer.engine.get_config", lambda: cfg)
    snapshots = []

    async def capture(session):
        tree = await capture_axtree(session)
        snapshots.append(tree)
        return tree

    monkeypatch.setattr("cliany_site.explorer.engine.capture_axtree", capture)
    calls = 0

    def ref(name, role):
        return next((key, item) for key, item in snapshots[-1]["selector_map"].items()
                    if item.get("name") == name and item.get("role") == role)

    async def respond(_messages):
        nonlocal calls
        calls += 1
        read = {"type": "extract", "selector": "#results li", "extract_mode": "list", "fields": {"name": "span"}}
        if calls == 1:
            _, link = ref("Alpha results", "link")
            initial = dict(read)
            if first_purpose:
                initial["purpose"] = first_purpose
            reply = {"actions": [{"type": "navigate", "url": urljoin(scope_search, link["attributes"]["href"])},
                                  initial], "done": False}
        else:
            assert calls == 2
            reply = {"actions": [{"type": "type", "ref": ref("Search", "textbox")[0], "value": "Alpha"},
                                  {"type": "click", "ref": ref("Search", "button")[0]}, read], "done": True,
                     "commands": [{"name": "search-items", "description": "Search items", "expects_nonempty": False,
                        "action_steps": [0, 2, 3, 4] if first_purpose == "probe" else [0, 1, 2, 3, 4],
                        "args": [{"name": "query", "required": True, "default": "Alpha", "action_index": 2}]}]}
        return SimpleNamespace(content=json.dumps(reply))

    model = SimpleNamespace(model="fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    domain = f"127.0.0.1_{urlparse(scope_search).port}"
    workflow = ("Read the fixed Alpha baseline and search the supplied query; return both scopes"
                if first_purpose == "baseline" else "Search the supplied query and return one result collection")
    async with playwright_api.async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"], viewport={"width": 1280, "height": 900},
        )
        normal_browser = None
        try:
            if first_purpose is None:
                with pytest.raises(ExploreContractError) as caught:
                    await WorkflowExplorer(cdp_url=endpoint).explore(scope_search, workflow, record=False)
                assert caught.value.reason == "collection_input_scope_invalid" and calls == 2
                assert not (home / "adapters").exists()
                return
            result = await WorkflowExplorer(cdp_url=endpoint).explore(scope_search, workflow, record=False)
            assert len(result.actions) == 5 and result.actions[1].purpose == first_purpose and calls == 2
            save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": scope_search}, result)
            directory = home / "adapters" / domain
            metadata = json.loads((directory / "metadata.json").read_text())
            assert metadata["commands"][0]["action_steps"] == result.commands[0].action_steps
            if first_purpose == "probe":
                assert len(metadata["exploration_history"][0]["actions"]) == 5
                assert metadata["exploration_history"][0]["actions"][1]["purpose"] == "probe"
                assert len(metadata["commands"][0]["actions"]) == 4
            else:
                assert metadata["commands"][0]["actions"][1]["purpose"] == "baseline"
            before = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json", "manifest.json") if (directory / name).is_file()}
            normal_browser = await playwright.chromium.launch(headless=True, env={**os.environ, **BROWSER_HOME})
            normal_page = await normal_browser.new_page()
            for query in ("Gamma", "Delta", "no-match"):
                await normal_page.goto(result.actions[0].target_url)
                baseline = [{"name": name}
                            for name in await normal_page.locator("#results li span").all_text_contents()]
                await normal_page.get_by_role("textbox", name="Search").fill(query)
                await normal_page.get_by_role("button", name="Search").click()
                expected = [{"name": name}
                            for name in await normal_page.locator("#results li span").all_text_contents()]
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "cliany_site", "--cdp-url", endpoint, domain, "search-items",
                    "--query", query, "--json", cwd=tmp_home, env=os.environ.copy(),
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, _stderr = await asyncio.wait_for(process.communicate(), 45)
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise
                payload = json.loads(stdout)
                (tmp_home / f"{first_purpose}-{query}-cli.json").write_text(json.dumps(payload, indent=2))
                assert process.returncode == 0 and payload["ok"] is True, payload
                actual = [step["data"]["content"] for step in payload["data"]["results"]
                          if step["command"] == "browser extract"]
                assert actual == ([baseline, expected] if first_purpose == "baseline" else [expected])
            assert before == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in before}
        finally:
            if normal_browser is not None:
                await normal_browser.close()
            await context.close()
