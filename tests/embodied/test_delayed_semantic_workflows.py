import asyncio
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.browser.cdp import CDPConnection
from cliany_site.browser.selector import ground_extract_target
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.fixture
def delayed_catalog():
    state = {"phase": "ready"}
    template = """<!doctype html><html><body data-phase=__PHASE__>
    <h1>Package catalog</h1><button onclick="openSearch()">Open search</button>
    <section id="work"><form onsubmit="search(event)">
      <input aria-label="Search" name="query"><button>Search</button>
    </form><h2>Search Results</h2><ul id="results" aria-label="Package results"><li>Beta toolkit</li></ul></section>
    <ul aria-label="Favorites"><li>Unrelated favorite</li></ul>
    <script>
    const phase = __PHASE__;
    function openSearch() {
      document.getElementById('work').replaceChildren();
      setTimeout(() => {
        document.getElementById('work').innerHTML =
          '<form onsubmit="search(event)"><input aria-label="Search" name="query"><button>Search</button></form>';
      }, phase === 'type' ? 4000 : 0);
    }
    function search(event) {
      event.preventDefault();
      document.body.dataset.submitHits = String(Number(document.body.dataset.submitHits || '0') + 1);
      const value = event.target.elements.query.value;
      document.getElementById('work').querySelectorAll('h2,ul').forEach(node => node.remove());
      const heading = document.createElement('h2');
      heading.textContent = 'Searching'; document.getElementById('work').append(heading);
      setTimeout(() => {
        const list = document.createElement('ul'); list.id = 'results';
        list.setAttribute('aria-label','Package results');
        const row = document.createElement('li'); row.textContent = value + ' toolkit'; list.append(row);
        document.getElementById('work').append(list); heading.textContent = 'Search Results';
      }, phase === 'list' ? 4000 : 0);
    }
    </script></body></html>"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = template.replace("__PHASE__", json.dumps(state["phase"])).encode()
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
        yield f"http://127.0.0.1:{server.server_address[1]}/", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.embodied
@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["type", "list"])
async def test_generated_workflow_waits_for_delayed_semantic_regions(
    tmp_home, clean_env, no_llm, monkeypatch, delayed_catalog, unused_tcp_port, phase
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    runtime = tmp_home / "runtime"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(runtime))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_NO_AGENT_MD", "1")
    url, state = delayed_catalog
    domain = f"127.0.0.1_{url.split(':')[-1].strip('/')}"
    cdp_url = f"ws://127.0.0.1:{unused_tcp_port}"
    cdp = CDPConnection(cdp_url=cdp_url)
    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"]
        )
        try:
            page = await browser.new_page()
            await page.goto(url)
            tree = await capture_axtree(await cdp.connect())
            target = ground_extract_target("#results", tree["selector_map"], tree["extract_candidates"])
            assert target and target["name"] == "Package results"
            result = ExploreResult(
                pages=[PageInfo(url, "Package catalog")],
                actions=[
                    ActionStep("click", url, target_name="Open search", target_role="button"),
                    ActionStep("type", url, value="{{query}}", target_name="Search", target_role="textbox"),
                    ActionStep("click", url, target_name="Search", target_role="button"),
                    ActionStep("extract", url, selector="#results", extract_mode="list",
                               fields_map={"name": ""}, extract_target=target),
                ],
                commands=[CommandSuggestion("search-packages", "Search packages",
                                            [{"name": "query", "type": "str", "description": "Filter"}],
                                            [0, 1, 2, 3])],
            )
            save_adapter(domain, AdapterGenerator().generate(result, domain), explore_result=result)
            files = runtime / "adapters" / domain
            before = {name: hashlib.sha256((files / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json")}
            state["phase"] = phase
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", cdp_url,
                domain, "search-packages", "--query", "Gamma", "--json", cwd=tmp_home,
                env=os.environ.copy(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _stderr = await asyncio.wait_for(process.communicate(), 45)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            payload = json.loads(stdout)
            (tmp_home / "replay-result.json").write_text(json.dumps(payload, indent=2))
            assert before == {name: hashlib.sha256((files / name).read_bytes()).hexdigest() for name in before}
            observer = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{unused_tcp_port}")
            try:
                pages = [page for context in observer.contexts for page in context.pages if page.url == url]
                current = [page for page in pages if await page.locator("body").get_attribute("data-phase") == phase]
                assert len(current) == 1
                actual = current[0]
                if phase == "type":
                    await actual.get_by_role("textbox", name="Search", exact=True).wait_for(timeout=6000)
                else:
                    await actual.get_by_role("list", name="Package results", exact=True).wait_for(timeout=6000)
                assert process.returncode == 0 and payload["ok"] is True, payload
                assert payload["data"]["results"][-1]["data"]["content"] == [{"name": "Gamma toolkit"}]
                assert await actual.get_by_role("textbox", name="Search", exact=True).input_value() == "Gamma"
                assert await actual.get_by_role("list", name="Package results", exact=True).inner_text() == (
                    "Gamma toolkit"
                )
                assert await actual.locator("body").get_attribute("data-submit-hits") == "1"
            finally:
                await observer.close()
        finally:
            await cdp.disconnect()
            await browser.close()
