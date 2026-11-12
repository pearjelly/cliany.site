import asyncio
import importlib.util
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from cliany_site.browser.axtree import capture_axtree
from cliany_site.browser.cdp import CDPConnection
from cliany_site.browser.selector import ground_extract_target, replayable_extract_selectors, resolve_extract_target
from cliany_site.codegen.generator import AdapterGenerator, save_adapter
from cliany_site.explorer.models import ActionStep, CommandSuggestion, ExploreResult, PageInfo
from cliany_site.extract import build_semantic_extract_js, prepare_semantic_extract_selector

playwright_api = pytest.importorskip("playwright.async_api")
BROWSER_HOME = {key: os.environ[key] for key in ("HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH") if key in os.environ}


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_fresh_browser_replay_invalidates_observed_backend_refs(tmp_home, clean_env, no_llm, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "semantic_benchmark", Path(__file__).with_name("run_live_benchmark.py")
    )
    assert spec and spec.loader
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    state = {"shift": True}
    with benchmark._serve_pages(state) as base:
        async with playwright_api.async_playwright() as playwright:
            port = benchmark._free_port()
            browser = await playwright.chromium.launch(headless=True, args=[f"--remote-debugging-port={port}"])
            cdp = CDPConnection(cdp_url=f"ws://127.0.0.1:{port}")
            try:
                url = f"{base}/filter_catalog.html"
                await benchmark._prime_filter_replay(browser, port, url, state)
                session = await cdp.connect()
                original = await capture_axtree(session)
                await session.navigate_to(url, new_tab=False)
                page = browser.contexts[-1].pages[-1]
                await page.get_by_label("Filter packages").fill("gamma")
                await page.get_by_role("button", name="Search", exact=True).click()
                changed = await capture_axtree(session)
                def search_ref(tree):
                    return next(k for k, v in tree["selector_map"].items() if v.get("name") == "Search")
                assert search_ref(original) != search_ref(changed)
                assert any(c["root_selector"] == "#matched-packages" for c in changed["extract_candidates"]), changed
                assert state["shift"] is True
            finally:
                await cdp.disconnect()
                await browser.close()


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
async def test_main_result_list_is_distinct_from_pagination_and_nested_metadata(
    tmp_home, clean_env, no_llm, monkeypatch, changing_catalog, unused_tcp_port
):
    url, _ = changing_catalog
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    cdp = CDPConnection(cdp_url=f"ws://127.0.0.1:{unused_tcp_port}")
    result_list = """
        <ol><li><h2><a href="/crates/alpha">Alpha</a></h2>
            <ul aria-label="Statistics"><li><a href="/history">Release history</a></li></ul></li>
            <li style="margin-top: 2500px"><h2><a href="/crates/beta">Beta</a></h2></li></ol>
    """
    pagination = '<nav aria-label="Pagination"><ol><li><a href="?page=2">Next</a></li></ol></nav>'
    footer = '<footer><ul id="elsewhere"><li><a href="/about">About</a></li></ul></footer>'
    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"]
        )
        try:
            page = await browser.new_page()
            await page.goto(url)
            await page.set_content(
                f'<div style="display: contents"><main><h1>Search Results</h1>'
                f'<div>{result_list}{pagination}</div></main></div>{footer}'
            )
            session = await cdp.connect()
            tree = await capture_axtree(session)
            refs, candidates = tree["selector_map"], tree["extract_candidates"]
            scoped = [item for item in candidates if item["root_selector"].startswith("main ")]
            assert len(scoped) == 1, candidates
            root = scoped[0]["root_selector"]
            assert root in replayable_extract_selectors(refs, candidates)
            target = ground_extract_target(f"{root} li", refs, candidates)
            assert target and target["suffix"] == ""
            selector, error = await prepare_semantic_extract_selector(session, target, "list")
            assert error is None and selector == root
            script = build_semantic_extract_js(selector, "list", {"name": "h2 a", "url": "h2 a@href"}, target)
            assert await page.evaluate(script) == [
                {"name": "Alpha", "url": "/crates/alpha"}, {"name": "Beta", "url": "/crates/beta"},
            ]

            # The same identity survives a new result row and a different list tag and wrapper.
            changed = '<ul><li><h2><a href="/crates/gamma">Gamma</a></h2></li></ul>'
            await page.set_content(f"<main><article>{changed}</article></main>{footer}")
            selector, error = await prepare_semantic_extract_selector(session, target, "list")
            assert error is None and selector == root
            assert await page.evaluate(script) == [{"name": "Gamma", "url": "/crates/gamma"}]

            for html in (
                f"<main>{changed}{result_list}</main>{footer}",
                f'<main>{changed}<div role="list"><div role="listitem">Other results</div></div></main>{footer}',
                f"<main>{changed}</main><main>{result_list}</main>{footer}",
                f"<main>{changed}</main><main><p>Another main</p></main>{footer}",
                f"<main><h1>Search Results</h1><p>0 crates found.</p><ol></ol></main>{footer}",
                f'<main><ol><li><a href="/about">Navigation only</a></li></ol></main>{footer}',
                '<main><ol><li><h2 role="presentation"><a href="/about">Not a heading</a></h2></li></ol></main>'
                + footer,
                f'<main><ol><li><ul><li><h2><a href="/about">Nested only</a></h2></li></ul></li></ol></main>{footer}',
                f'<main><div style="opacity: 0">{changed}</div></main>{footer}',
            ):
                await page.set_content(html)
                current = await capture_axtree(session)
                assert resolve_extract_target(target, current["selector_map"], current["extract_candidates"]) is None
                assert await page.evaluate(script) == {"__cliany_extract_target_missing__": True}
        finally:
            await cdp.disconnect()
            await browser.close()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_scoped_search_replay_requires_explicit_zero_for_the_bound_query(
    tmp_home, clean_env, no_llm, monkeypatch, changing_catalog, unused_tcp_port
):
    url, _ = changing_catalog
    monkeypatch.setenv("CLIANY_RUNTIME_HOME", str(tmp_home / "runtime"))
    for key, value in BROWSER_HOME.items():
        monkeypatch.setenv(key, value)
    cdp = CDPConnection(cdp_url=f"ws://127.0.0.1:{unused_tcp_port}")
    empty = '<h2>0 crates found. <a href="/help">Get started</a> and create your own.</h2>'
    title = "<h1>Search Results<span> for 'no-result'</span></h1>"
    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, env={**os.environ, **BROWSER_HOME}, args=[f"--remote-debugging-port={unused_tcp_port}"]
        )
        try:
            page = await browser.new_page()
            await page.goto(f"{url}?q=alpha")
            await page.set_content(
                "<main><h1>Search Results for 'alpha'</h1>"
                '<ol><li><h2><a href="/crates/alpha">Alpha</a></h2></li></ol></main>'
            )
            session = await cdp.connect()
            tree = await capture_axtree(session)
            candidates = tree["extract_candidates"]
            root = next(item["root_selector"] for item in candidates if item.get("scope"))
            target = ground_extract_target(root, tree["selector_map"], candidates)
            assert target
            target["empty_result"] = {
                "page": url, "parameter": "q", "heading_prefix": "Search Results for '", "heading_suffix": "'",
                "message": "0 crates found.", "query": "no-result",
            }
            await page.goto(f"{url}?q=no-result")
            await page.set_content(f"<main>{title}{empty}</main>")
            monkeypatch.setattr("cliany_site.extract._LIST_SETTLE_TIMEOUT_SECONDS", 3.0)
            selector, error = await prepare_semantic_extract_selector(session, target, "list")
            assert error is None and selector is not None
            script = build_semantic_extract_js(selector, "list", {"title": "h2 a", "url": "h2 a@href"}, target)
            assert await page.evaluate(script) == []
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "cliany_site", "--cdp-url", f"ws://127.0.0.1:{unused_tcp_port}",
                "browser", "extract", "--mode", "list", "--target-json", json.dumps(target), "--json",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=tmp_home,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), 30)
            except TimeoutError:
                process.kill()
                await process.communicate()
                raise
            assert process.returncode == 0, stderr.decode()
            payload = json.loads(stdout)
            assert payload["data"]["content"] == [] and payload["data"]["quality"]["status"] == "empty", payload

            rows = '<ol><li><h2><a href="/crates/other">Other</a></h2></li></ol>'
            await page.set_content(f"<main>{title}{rows}</main>")
            selector, error = await prepare_semantic_extract_selector(session, target, "list")
            assert error is None and selector == root
            positive_script = build_semantic_extract_js(selector, "list", {"title": "h2 a"}, target)
            assert await page.evaluate(positive_script) == [{"title": "Other"}]

            monkeypatch.setattr("cliany_site.extract._LIST_SETTLE_TIMEOUT_SECONDS", 0.3)
            for markup in (
                f"<main>{title}<p>No region yet</p></main>",
                f"<main><h1>Search Results for 'old'</h1>{empty}</main>",
                f'<main aria-busy="true">{title}{empty}</main>',
                f'<main>{title}<section hidden>{empty}</section></main>',
                f"<main>{title}{empty}{empty}</main>",
                f"<main>{title}{empty}<ol><li><a href='/old'>Old row</a></li></ol></main>",
                f"<main>{title}<nav>{empty}</nav></main>",
                f"<main>{title}{empty}</main><main>Another main</main>",
            ):
                await page.set_content(markup)
                selector, _ = await prepare_semantic_extract_selector(session, target, "list")
                assert selector is None, markup
                assert await page.evaluate(script) == {"__cliany_extract_target_missing__": True}, markup
            await page.goto(f"{url}?q=no-result&q=old")
            await page.set_content(f"<main>{title}{empty}</main>")
            assert await page.evaluate(script) == {"__cliany_extract_target_missing__": True}
        finally:
            await cdp.disconnect()
            await browser.close()


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
