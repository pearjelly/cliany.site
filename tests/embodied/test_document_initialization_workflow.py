import asyncio
import hashlib
import json
import os
import sys
import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.browser.cdp import CDPConnection
from cliany_site.browser.selector import ground_extract_target
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}
QUERY = "cliany-no-match-20261017-omega"


@pytest.fixture
def initializing_search():
    state = {"phase": "ready"}
    typed = Event()
    release_image = Event()
    form = """<!doctype html><html><body data-phase=__PHASE__>
    <form onsubmit="submitSearch(event)"><input name="q" aria-label="Search"><button>Search</button></form>
    <section><h2 id="status">Loading</h2><ul id="results" aria-label="Package results"><li>Preview</li></ul></section>
    <script>
    const field = document.querySelector('input[name="q"]'); let reported = false; let pending = false;
    field.addEventListener('input', () => {
      if (!reported && field.value.length >= __QUERY_LENGTH__) { reported = true; fetch('/typed'); }
    });
    function publish() {
      document.body.dataset.submitted = field.value;
      const results = document.getElementById('results'); results.replaceChildren();
      if (field.value) {
        const row=document.createElement('li'); row.textContent=field.value+' toolkit'; results.append(row);
      }
      document.getElementById('status').textContent = 'Search Results';
    }
    function submitSearch(event) {
      event.preventDefault();
      document.body.dataset.submits = String(Number(document.body.dataset.submits || '0') + 1);
      if (!document.body.dataset.initialized) { pending = true; return; }
      publish();
    }
    document.addEventListener('DOMContentLoaded', () => {
      document.body.dataset.resetValue = field.value;
      field.value = new URLSearchParams(location.search).get('q') || '';
      document.body.dataset.initialized = 'true';
      document.getElementById('status').textContent = 'Search Results';
      if (pending) publish();
    });
    </script><script defer src="/init.js"></script>__IMAGE__</body></html>"""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            content_type = "text/html; charset=utf-8"
            if path == "/search.html":
                body = form.replace("__PHASE__", json.dumps(state["phase"]))
                body = body.replace("__QUERY_LENGTH__", str(len(QUERY)))
                body = body.replace("__IMAGE__", '<img src="/slow.png" alt="Slow image">'
                                    if state["phase"] == "image" else "").encode()
            elif path == "/init.js":
                if state["phase"] == "defer":
                    typed.wait(2)
                    time.sleep(0.12)
                content_type = "application/javascript"
                body = b"window.deferredScriptFinished = true;"
            elif path == "/typed":
                typed.set()
                body = b"ok"
            elif path == "/slow.png":
                release_image.wait(30)
                body = b""
            else:
                body = b'<!doctype html><a href="/search.html">Search page</a>'
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/", state
    finally:
        typed.set()
        release_image.set()
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.embodied
@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["defer", "image"])
async def test_generated_query_survives_document_initialization_without_waiting_for_images(
    tmp_home, clean_env, no_llm, monkeypatch, initializing_search, unused_tcp_port, phase
):
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_NO_AGENT_MD", "1")
    url, state = initializing_search
    domain = f"127.0.0.1_{url.split(':')[-1].strip('/')}"
    cdp_url = f"ws://127.0.0.1:{unused_tcp_port}"
    cdp = CDPConnection(cdp_url=cdp_url)
    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"]
        )
        try:
            page = await browser.new_page()
            await page.goto(url + "search.html")
            tree = await capture_axtree(await cdp.connect())
            target = ground_extract_target("#results", tree["selector_map"], tree["extract_candidates"])
            assert target and target["name"] == "Package results"
            result = ExploreResult(
                pages=[PageInfo(url, "Search home"), PageInfo(url + "search.html", "Search")],
                actions=[
                    ActionStep("click", url, target_name="Search page", target_role="link"),
                    ActionStep("type", url + "search.html", value="{{query}}",
                               target_name="Search", target_role="textbox"),
                    ActionStep("click", url + "search.html", target_name="Search", target_role="button"),
                    ActionStep("extract", url + "search.html", selector="#results", extract_mode="list",
                               fields_map={"name": ""}, extract_target=target),
                ],
                commands=[CommandSuggestion("search-packages", "Search packages",
                                            [{"name": "query", "type": "str", "description": "Query"}],
                                            [0, 1, 2, 3])],
            )
            save_adapter(domain, AdapterGenerator().generate(result, domain), explore_result=result)
            files = tmp_home / "runtime" / "adapters" / domain
            before = {name: hashlib.sha256((files / name).read_bytes()).hexdigest()
                      for name in ("commands.py", "metadata.json")}
            state["phase"] = phase
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", cdp_url,
                domain, "search-packages", "--query", QUERY, "--json", cwd=tmp_home,
                env=os.environ.copy(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _stderr = await asyncio.wait_for(process.communicate(), 25)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            payload = json.loads(stdout)
            assert before == {name: hashlib.sha256((files / name).read_bytes()).hexdigest() for name in before}
            (tmp_home / "initialization-result.json").write_text(json.dumps(payload, indent=2))
            observer = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{unused_tcp_port}")
            try:
                current = [page for context in observer.contexts for page in context.pages
                           if page.url == url + "search.html"
                           and await page.locator("body").get_attribute("data-phase") == phase]
                assert len(current) == 1
                actual = current[0]
                observed = await actual.evaluate("""() => ({query:document.body.dataset.submitted,
                    submits:document.body.dataset.submits,resetValue:document.body.dataset.resetValue,
                    ready:document.readyState,dcl:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd})""")
                (tmp_home / "initialization-dom.json").write_text(json.dumps(observed, indent=2))
                assert process.returncode == 0 and payload["ok"] is True, payload
                assert payload["data"]["results"][-1]["data"]["content"] == [{"name": QUERY + " toolkit"}]
                assert observed["query"] == QUERY and observed["submits"] == "1", observed
                if phase == "image":
                    assert observed["ready"] == "interactive" and observed["dcl"] > 0, observed
            finally:
                await observer.close()
        finally:
            await cdp.disconnect()
            await browser.close()
