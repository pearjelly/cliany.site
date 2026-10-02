"""Independent page-state oracles for the controlled exploration tasks."""

import json
from pathlib import Path

import pytest

from cliany_site.extract import build_extract_js

playwright_async_api = pytest.importorskip("playwright.async_api")
async_playwright = playwright_async_api.async_playwright
CASES = {
    case["id"]: case
    for case in json.loads(Path(__file__).with_name("explore_benchmark_cases.json").read_text())["tasks"]
}


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_form_result_oracle(benchmark_server):
    case = CASES["form-result"]
    replay = case["replays"][0]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{benchmark_server}{case['path']}")
            await page.get_by_label("Name").fill(replay["args"]["name"])
            await page.get_by_label("Color").select_option(label=replay["args"]["color"])
            await page.get_by_role("button", name="Apply").click()
            assert await page.locator("#result").text_content() == replay["expected_text"]
        finally:
            await browser.close()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_filter_catalog_oracle(benchmark_server):
    case = CASES["filter-catalog"]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{benchmark_server}{case['path']}")
            for replay in case["replays"]:
                await page.get_by_label("Filter packages").fill(replay["args"]["query"])
                await page.get_by_role("button", name="Search").click()
                assert await page.locator("#summary").text_content() == replay["expected_summary"]
                assert await page.locator("#results li").all_text_contents() == replay["expected_rows"]
                assert await page.locator("#results li").evaluate_all(
                    "rows => rows.map(row => row.dataset.code)"
                ) == replay["expected_codes"]
                expected = [{"name": name} for name in replay["expected_rows"]]
                assert await page.evaluate(build_extract_js("#results", "list", {"name": ""})) == expected
                assert await page.evaluate(build_extract_js("#results", "list")) == replay["expected_rows"]
                assert await page.evaluate(build_extract_js("#results li", "list", {"name": ""})) == expected
        finally:
            await browser.close()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_semantic_reorder_oracle(benchmark_server):
    case = CASES["semantic-reorder"]
    replay = case["replays"][0]
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            for expected_noise in (1, 2):
                page = await browser.new_page()
                await page.goto(f"{benchmark_server}{case['path']}")
                assert await page.locator("#controls button").count() == expected_noise + 1
                await page.get_by_role("button", name="Inspect Beta").click()
                assert await page.locator("#result").text_content() == replay["expected_text"]
                assert await page.locator("#result").get_attribute("data-hits") == "1"
                await page.close()
        finally:
            await browser.close()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_semantic_reorder_changes_target_axtree_ref(benchmark_server, unused_tcp_port):
    from cliany_site.browser.axtree import capture_axtree
    from cliany_site.browser.cdp import CDPConnection

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, args=[f"--remote-debugging-port={unused_tcp_port}"]
        )
        cdp = CDPConnection(cdp_url=f"ws://127.0.0.1:{unused_tcp_port}", headless=True)
        try:
            assert await cdp.check_available()
            browser_session = await cdp.connect()
            refs = []
            for _ in range(2):
                await browser_session.navigate_to(f"{benchmark_server}/semantic_reorder.html", new_tab=False)
                tree = await capture_axtree(browser_session)
                target = [
                    element["ref"]
                    for element in tree["selector_map"].values()
                    if element.get("role") == "button" and element.get("name") == "Inspect Beta"
                ]
                assert len(target) == 1
                refs.append(target[0])
            assert refs[0] != refs[1]
        finally:
            await cdp.disconnect()
            await browser.close()
