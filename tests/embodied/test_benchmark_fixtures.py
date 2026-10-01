"""Independent page-state oracles for the controlled exploration tasks."""

import pytest

playwright_async_api = pytest.importorskip("playwright.async_api")
async_playwright = playwright_async_api.async_playwright


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_filter_catalog_oracle(benchmark_server):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(f"{benchmark_server}/filter_catalog.html")
            await page.get_by_label("Filter packages").fill("beta")
            await page.get_by_role("button", name="Search").click()
            assert await page.locator("#summary").text_content() == "1 matches"
            assert await page.locator("#results li").evaluate_all(
                "rows => rows.map(row => row.dataset.code)"
            ) == ["beta"]

            await page.get_by_label("Filter packages").fill("no-such-package")
            await page.get_by_role("button", name="Search").click()
            assert await page.locator("#summary").text_content() == "0 matches"
            assert await page.locator("#results li").count() == 0
        finally:
            await browser.close()


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_semantic_reorder_oracle(benchmark_server):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            for expected_noise in (1, 2):
                page = await browser.new_page()
                await page.goto(f"{benchmark_server}/semantic_reorder.html")
                assert await page.locator("#controls button").count() == expected_noise + 1
                await page.get_by_role("button", name="Inspect Beta").click()
                assert await page.locator("#result").text_content() == "Beta"
                assert await page.locator("#result").get_attribute("data-hits") == "1"
                await page.close()
        finally:
            await browser.close()
