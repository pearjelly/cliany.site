"""Independent page-state oracles for the controlled exploration tasks."""

import json
from pathlib import Path

import pytest

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
