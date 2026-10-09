import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.browser.cdp import CDPConnection
from cliany_site.browser.selector import ground_extract_target
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.extract import build_semantic_extract_js

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.fixture
def changing_catalog():
    original = Path(__file__).with_name("pages").joinpath("filter_catalog.html").read_text()
    state = {"mode": "original"}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            html = original
            if state["mode"] != "original":
                html = html.replace("'results'", "'matched-packages'").replace('id="results"', 'id="matched-packages"')
                html = html.replace("'summary'", "'match-total'").replace('id="summary"', 'id="match-total"')
                html = html.replace(
                    "<body>",
                    '<body><button>Other control</button>'
                    '<ul id="results" aria-label="Favorites"><li>Unrelated favorite</li></ul>',
                )
            if state["mode"] == "missing":
                html = html.replace('<ul id="matched-packages" aria-label="Package results"></ul>', "")
                html = html.replace(
                    "results.replaceChildren();",
                    "if (!results) { document.getElementById('match-total').textContent = "
                    "`${matches.length} matches`; return; } results.replaceChildren();",
                )
            if state["mode"] == "ambiguous":
                html = html.replace(
                    "</body>", '<ul id="duplicate" aria-label="Package results"><li>Wrong duplicate</li></ul></body>'
                )
            if state["mode"] == "delayed":
                html = html.replace(
                    "document.getElementById('match-total').textContent = `${matches.length} matches`;",
                    "document.getElementById('match-total').textContent = `${matches.length} matches`;"
                    "setTimeout(() => { results.id = 'final-packages'; }, 2500);",
                )
            body = html.encode()
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
        yield f"http://127.0.0.1:{server.server_address[1]}/", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_generated_count_and_names_survive_layout_ref_changes_and_fail_closed(
    tmp_home, clean_env, no_llm, monkeypatch, changing_catalog, unused_tcp_port
):
    url, state = changing_catalog
    domain = f"127.0.0.1_{url.split(':')[-1].strip('/')}"
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    monkeypatch.setenv("CLIANY_QA_OFFLINE", "1")
    monkeypatch.setenv("CLIANY_NO_AGENT_MD", "1")
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    cdp_url = f"ws://127.0.0.1:{unused_tcp_port}"
    cdp = CDPConnection(cdp_url=cdp_url)
    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"]
        )
        try:
            page = await browser.new_page()
            await page.goto(url)
            await page.get_by_label("Filter packages").fill("beta")
            await page.get_by_role("button", name="Search", exact=True).click()
            session = await cdp.connect()
            original_tree = await capture_axtree(session)
            summary = ground_extract_target(
                "#summary", original_tree["selector_map"], original_tree["extract_candidates"]
            )
            rows = ground_extract_target("#results", original_tree["selector_map"], original_tree["extract_candidates"])
            assert summary and rows and rows["name"] == "Package results"
            assert await page.evaluate(build_semantic_extract_js("#results", "table", None, rows)) == {
                "__cliany_extract_mode_mismatch__": True,
            }
            result = ExploreResult(
                pages=[PageInfo(url, "Catalog")],
                actions=[
                    ActionStep("type", url, value="{{query}}", target_name="Filter packages", target_role="searchbox"),
                    ActionStep("click", url, target_name="Search", target_role="button"),
                    ActionStep("extract", url, selector="#summary", extract_mode="text", extract_target=summary),
                    ActionStep(
                        "extract",
                        url,
                        selector="#results",
                        extract_mode="list",
                        fields_map={"name": ""},
                        extract_target=rows,
                    ),
                ],
                commands=[
                    CommandSuggestion(
                        "search-packages",
                        "Search packages",
                        [{"name": "query", "description": "Filter", "type": "str"}],
                        [0, 1, 2, 3],
                        expects_nonempty=False,
                    )
                ],
            )
            save_adapter(domain, AdapterGenerator().generate(result, domain), explore_result=result)
            for mode, query, expected in [
                ("renamed", "gamma", ["Gamma toolkit"]),
                ("renamed", "no-such-package", []),
                ("delayed", "gamma", ["Gamma toolkit"]),
                ("ambiguous", "gamma", None),
                ("missing", "gamma", None),
            ]:
                state["mode"] = mode
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "-m",
                    "cliany_site",
                    "--cdp-url",
                    cdp_url,
                    domain,
                    "search-packages",
                    "--query",
                    query,
                    "--json",
                    cwd=tmp_home,
                    env=os.environ.copy(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, _stderr = await asyncio.wait_for(process.communicate(), 60)
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise
                payload = json.loads(stdout)
                if expected is None:
                    assert process.returncode != 0 and payload["ok"] is False, payload
                    assert payload["error"]["code"] == "E_SELECTOR_NOT_FOUND", payload
                    continue
                assert process.returncode == 0 and payload["ok"] is True, payload
                assert payload["data"]["results"][-2]["data"]["content"] == {"text": f"{len(expected)} matches"}
                assert payload["data"]["results"][-1]["data"]["content"] == [{"name": name} for name in expected]
                oracle = await browser.new_page()
                await oracle.goto(url)
                await oracle.get_by_label("Filter packages").fill(query)
                await oracle.get_by_role("button", name="Search", exact=True).click()
                assert (
                    await oracle.get_by_role("list", name="Package results").locator("li").all_text_contents()
                    == expected
                )
                assert await oracle.get_by_role("status").text_content() == f"{len(expected)} matches"
                await oracle.close()
            state["mode"] = "renamed"
            await session.navigate_to(url, new_tab=False)
            changed_tree = await capture_axtree(session)

            def search_ref(tree):
                return next(
                    k
                    for k, v in tree["selector_map"].items()
                    if v.get("role") == "button" and v.get("name") == "Search"
                )

            assert search_ref(original_tree) != search_ref(changed_tree)
        finally:
            await cdp.disconnect()
            await browser.close()
