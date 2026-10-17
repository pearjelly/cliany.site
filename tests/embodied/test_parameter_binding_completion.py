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
def parameter_search():
    body = b"""<!doctype html><html><body>
    <a href="?q=Alpha">Alpha results</a>
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
      if (query === 'no-match') return;
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
async def test_fixed_navigation_binding_is_replanned_to_real_changed_and_zero_inputs(
    tmp_home, clean_env, no_llm, monkeypatch, parameter_search, unused_tcp_port,
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_NO_AGENT_MD", "1")
    cfg = replace(get_config(), explore_max_steps=3, llm_retry_max_attempts=1, vision_enabled=False)
    monkeypatch.setattr("cliany_site.explorer.engine.get_config", lambda: cfg)
    snapshots = []

    async def capture(session):
        tree = await capture_axtree(session)
        snapshots.append(tree)
        return tree

    monkeypatch.setattr("cliany_site.explorer.engine.capture_axtree", capture)

    def element(name, role):
        return next((key, value) for key, value in snapshots[-1]["selector_map"].items()
                    if value.get("name") == name and value.get("role") == role)

    calls = 0

    async def respond(_messages):
        nonlocal calls
        calls += 1
        read = {"type": "extract", "selector": "#results li", "extract_mode": "list", "fields": {"name": "span"}}
        if calls == 1:
            from urllib.parse import urljoin

            _, link = element("Alpha results", "link")
            actions = [{"type": "navigate", "url": urljoin(parameter_search, link["attributes"]["href"])}, read]
        else:
            assert calls == 2
            actions = [{"type": "type", "ref": element("Search", "textbox")[0], "value": "Alpha"},
                       {"type": "click", "ref": element("Search", "button")[0]}, read]
        return SimpleNamespace(content=json.dumps({"done": True, "actions": actions, "commands": [{
            "name": "search-packages", "action_steps": list(range(len(actions))), "expects_nonempty": False,
            "args": [{"name": "query", "required": True, "action_index": 0, "default": "Alpha"}],
        }]}))

    model = SimpleNamespace(model="deterministic-fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    domain = f"127.0.0.1_{urlparse(parameter_search).port}"
    async with playwright_api.async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, viewport={"width": 1280, "height": 900},
            env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            result = await WorkflowExplorer(cdp_url=endpoint).explore(parameter_search, "Search packages", record=False)
            save_adapter(domain, AdapterGenerator().generate(result, domain), {"source_url": parameter_search}, result)
            directory = runtime / "adapters" / domain
            before = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json", "manifest.json") if (directory / name).is_file()}
            for query in ("Gamma", "no-match"):
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "cliany_site", "--cdp-url", endpoint,
                    domain, "search-packages", "--query", query, "--json", cwd=tmp_home,
                    env=os.environ.copy(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, _stderr = await asyncio.wait_for(process.communicate(), 30)
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise
                payload = json.loads(stdout)
                (tmp_home / f"binding-native-{query}-cli.json").write_text(json.dumps(payload, indent=2))
                observer = await playwright.chromium.connect_over_cdp(endpoint)
                try:
                    pages = [page for ctx in observer.contexts for page in ctx.pages if "search" in page.url]
                    observed = [{"url": page.url, "query": await page.locator("body").get_attribute("data-query"),
                                 "submits": await page.locator("body").get_attribute("data-submits"),
                                 "rows": await page.locator("#results li span").all_text_contents()} for page in pages]
                    (tmp_home / f"binding-native-{query}-dom.json").write_text(json.dumps(observed, indent=2))
                    assert process.returncode == 0 and payload["ok"] is True, payload
                    extracts = [step["data"]["content"] for step in payload["data"]["results"]
                                if step["command"] == "browser extract"]
                    expected = [] if query == "no-match" else [
                        {"name": query + " " + suffix} for suffix in ("toolkit", "helper", "extra")]
                    assert extracts == [expected], {"returned": extracts, "observed": observed}
                    actual = next(page for page in observed if page["url"] == parameter_search + "?q=" + query)
                    assert actual["rows"] == [row["name"] for row in expected]
                    assert actual["query"] == query and actual["submits"] == "1"
                finally:
                    await observer.close()
            assert before == {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in before}
            assert calls == 2 and [action.action_type for action in result.actions] == ["type", "click", "extract"]
            assert result.commands[0].args[0]["action_index"] == 0
        finally:
            await context.close()


@pytest.mark.embodied
@pytest.mark.parametrize("correction", ["unbind", "clobber"])
async def test_shared_repair_cannot_keep_a_dead_or_overwritten_query(
    correction, tmp_home, clean_env, no_llm, monkeypatch, parameter_search, unused_tcp_port,
):
    from cliany_site.errors import ExploreContractError

    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
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

    async def respond(_messages):
        nonlocal calls
        calls += 1
        assert calls <= 2
        def element(name, role):
            return next((key, value) for key, value in snapshots[-1]["selector_map"].items()
                        if value.get("name") == name and value.get("role") == role)
        from urllib.parse import urljoin

        _, link = element("Alpha results", "link")
        actions = [{"type": "navigate", "url": urljoin(parameter_search, link["attributes"]["href"])}]
        args = [{"name": "query", "required": True, "action_index": 0, "default": "Alpha"}]
        if calls == 2 and correction == "unbind":
            args = [{"name": "query", "required": True}]
        elif calls == 2:
            actions = [{"type": "type", "ref": element("Search", "textbox")[0], "value": "Alpha"},
                       {"type": "click", "ref": element("Search", "button")[0]}]
            args.append({"name": "other", "action_index": 0})
        return SimpleNamespace(content=json.dumps({"done": True, "actions": actions, "commands": [{
            "name": "open-results", "action_steps": list(range(len(actions))), "args": args,
        }]}))

    model = SimpleNamespace(model="deterministic-fixture", ainvoke=AsyncMock(side_effect=respond))
    monkeypatch.setattr("cliany_site.explorer.engine._get_llm", lambda **_kwargs: model)
    endpoint = f"http://127.0.0.1:{unused_tcp_port}"
    async with playwright_api.async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(tmp_home / "profile"), headless=True, env={**os.environ, **BROWSER_HOME},
            args=[f"--remote-debugging-port={unused_tcp_port}"],
        )
        try:
            with pytest.raises(ExploreContractError) as caught:
                await WorkflowExplorer(cdp_url=endpoint).explore(parameter_search, "Open results", record=False)
            assert caught.value.reason == "parameter_binding_invalid" and calls == 2
            page = next(page for page in context.pages if page.url == parameter_search)
            assert await page.get_by_role("textbox", name="Search").input_value() == ""
            assert await page.locator("body").get_attribute("data-submits") is None
            assert not (tmp_home / "runtime" / "adapters").exists()
        finally:
            await context.close()
