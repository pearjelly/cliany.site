"""Field selectors must not borrow text or links from neighboring results."""

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from cliany_site.extract import build_extract_js
from cliany_site.extract_quality import evaluate_extract_quality

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "search_extraction_gap.html"
FIELDS = {"title": ".result-title", "url": ".result-link@href", "snippet": ".result-snippet"}


@pytest.mark.embodied
@pytest.mark.asyncio
async def test_missing_result_fields_remain_blank():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(FIXTURE.read_text(encoding="utf-8"))
            rows = await page.evaluate(build_extract_js("article.result-card", "list", FIELDS))
        finally:
            await browser.close()

    assert rows[0] == {
        "title": "Alpha README", "url": "https://example.com/alpha", "snippet": "包含 README 和安装说明。",
    }
    assert rows[1]["url"] == ""
    assert rows[2]["snippet"] == ""
    quality = evaluate_extract_quality("list", rows, FIELDS)
    assert quality.ok is False
    assert quality.to_dict()["field_blank_rows"] == {"url": [2], "snippet": [3]}
