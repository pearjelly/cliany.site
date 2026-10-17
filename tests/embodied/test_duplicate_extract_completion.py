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
from urllib.parse import urlparse

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.config import get_config
from cliany_site.explorer.engine import WorkflowExplorer

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.fixture
def package_search():
    body = b"""<!doctype html><html><body>
    <form onsubmit="searchPackages(event)">
      <input name=q aria-label="Search"><button>Search</button>
    </form>
    <h2>Search Results</h2><ul id=results aria-label="Package results"><li><span>Preview</span></li></ul>
    <script>
    function searchPackages(event) {
      event.preventDefault(); const query = document.querySelector('input').value;
      history.replaceState(null, '', '?q='+encodeURIComponent(query));
      document.body.dataset.query = query;
      document.body.dataset.submits = String(Number(document.body.dataset.submits || '0')+1);
      const results = document.getElementById('results'); results.replaceChildren();
      for (const suffix of ['toolkit', 'helper', 'extra']) {
        const item = document.createElement('li'); const name = document.createElement('span');
        name.textContent = query+' '+suffix; item.append(name); results.append(item);
      }
    }
    </script></body></html>"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
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
@pytest.mark.asyncio
async def test_repeated_terminal_read_produces_one_changed_query_collection(
    tmp_home, clean_env, no_llm, monkeypatch, package_search, unused_tcp_port
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_NO_AGENT_MD", "1")
    cfg = replace(get_config(), explore_max_steps=4, llm_retry_max_attempts=1, vision_enabled=False)
    monkeypatch.setattr("cliany_site.explorer.engine.get_config", lambda: cfg)
    snapshots = []

    async def capture(session):
        tree = await capture_axtree(session)
        snapshots.append(tree)
        return tree

    monkeypatch.setattr("cliany_site.explorer.engine.capture_axtree", capture)
    fields = {"name": "span"}
    read = {"type": "extract", "selector": "#results li", "extract_mode": "list",
            "fields": fields, "description": "Read package results"}
    calls = 0

    def ref(name, role):
        return next(key for key, value in snapshots[-1]["selector_map"].items()
                    if value.get("name") == name and value.get("role") == role)

    async def respond(_messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            reply = {"actions": [
                {"type": "type", "ref": ref("Search", "textbox"), "value": "Alpha"},
                {"type": "click", "ref": ref("Search", "button")}, dict(read),
            ], "commands": [], "done": False}
        else:
            assert calls in (2, 3)
            count = 4 if calls == 2 else 3
            reply = {"actions": [dict(read)] if calls == 2 else [], "done": True, "commands": [{
                "name": "search-packages", "description": "Search packages", "action_steps": list(range(count)),
                "args": [{"name": "query", "required": True, "default": "Alpha", "action_index": 0}],
                "expects_nonempty": False,
            }]}
        return SimpleNamespace(content=json.dumps(reply))

    model = SimpleNamespace(model="deterministic-fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    domain = f"127.0.0.1_{urlparse(package_search).port}"
    async with playwright_api.async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, viewport={"width": 1280, "height": 900},
            env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            result = await WorkflowExplorer(cdp_url=endpoint).explore(package_search, "Search packages", record=False)
            save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": package_search}, result)
            directory = runtime / "adapters" / domain
            before = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json", "manifest.json") if (directory / name).is_file()}
            assert {"commands.py", "metadata.json"} <= before.keys()
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", endpoint,
                domain, "search-packages", "--query", "Gamma", "--json", cwd=tmp_home,
                env=os.environ.copy(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _stderr = await asyncio.wait_for(process.communicate(), 30)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            payload = json.loads(stdout)
            (tmp_home / "duplicate-native-cli.json").write_text(json.dumps(payload, indent=2))
            assert before == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in before}
            observer = await playwright.chromium.connect_over_cdp(endpoint)
            try:
                pages = [page for browser_context in observer.contexts for page in browser_context.pages
                         if page.url == package_search + "?q=Gamma"]
                assert len(pages) == 1
                actual = pages[0]
                observed = {"query": await actual.locator("body").get_attribute("data-query"),
                            "submits": await actual.locator("body").get_attribute("data-submits"),
                            "rows": await actual.locator("#results li span").all_text_contents(),
                            "generation_calls": model.ainvoke.await_count,
                            "actions": [action.action_type for action in result.actions]}
                (tmp_home / "duplicate-native-dom.json").write_text(json.dumps(observed, indent=2))
                expected = [{"name": "Gamma " + suffix} for suffix in ("toolkit", "helper", "extra")]
                assert process.returncode == 0 and payload["ok"] is True, payload
                returned = [row for step in payload["data"]["results"] if step["command"] == "browser extract"
                            for row in step["data"]["content"]]
                assert returned == expected, {"returned": returned, "observed": observed}
                assert observed["rows"] == [row["name"] for row in expected]
                assert observed["query"] == "Gamma" and observed["submits"] == "1"
                assert model.ainvoke.await_count == 3 and len(result.actions) == 3
            finally:
                await observer.close()
        finally:
            await context.close()
