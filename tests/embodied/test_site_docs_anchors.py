"""Native documentation fragments must remain below the sticky header."""

from pathlib import Path

import pytest

playwright_async_api = pytest.importorskip("playwright.async_api")
async_playwright = playwright_async_api.async_playwright
DOCS_URL = (Path(__file__).resolve().parents[2] / "site" / "docs" / "index.html").as_uri()
ANCHORS = ("install", "config", "quickstart")
pytestmark = [pytest.mark.embodied, pytest.mark.asyncio]


@pytest.fixture
async def docs_page(request):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            # Start Chrome before tmp_home replaces the process OS home.
            request.getfixturevalue("tmp_home")
            yield await browser.new_page(viewport={"width": 1280, "height": 900})
        finally:
            await browser.close()


async def assert_anchor_visible(page, anchor):
    assert await page.evaluate("location.hash") == f"#{anchor}"
    heading = page.locator(f"h2[id='{anchor}']")
    assert await heading.is_visible()
    rectangles = await heading.evaluate(
        """heading => {
            const target = heading.getBoundingClientRect();
            const header = document.querySelector('header').getBoundingClientRect();
            return {
                headingTop: target.top,
                headingBottom: target.bottom,
                headerBottom: header.bottom,
                viewportHeight: innerHeight,
                overflow: document.documentElement.scrollWidth > innerWidth,
                sticky: getComputedStyle(document.querySelector('header')).position,
            };
        }"""
    )
    assert rectangles["headingTop"] >= rectangles["headerBottom"], rectangles
    assert rectangles["headingBottom"] < rectangles["viewportHeight"], rectangles
    assert not rectangles["overflow"], rectangles
    assert rectangles["sticky"] == "sticky"


@pytest.mark.parametrize("width", [320, 390, 1280])
@pytest.mark.parametrize("anchor", ANCHORS)
async def test_direct_docs_fragment_and_reload(docs_page, width, anchor):
    await docs_page.set_viewport_size({"width": width, "height": 900})
    await docs_page.goto(f"{DOCS_URL}#{anchor}")
    await assert_anchor_visible(docs_page, anchor)
    await docs_page.reload()
    await assert_anchor_visible(docs_page, anchor)


@pytest.mark.parametrize("anchor", ANCHORS)
@pytest.mark.parametrize("keyboard", [False, True], ids=["click", "enter"])
async def test_desktop_sidebar_native_navigation(docs_page, anchor, keyboard):
    await docs_page.goto(DOCS_URL)
    heading = docs_page.locator(f"h2[id='{anchor}']")
    link = docs_page.get_by_role("navigation").get_by_role(
        "link", name=await heading.text_content(), exact=True
    )
    if keyboard:
        await link.focus()
        await link.press("Enter")
    else:
        await link.click()
    await assert_anchor_visible(docs_page, anchor)


@pytest.mark.parametrize("width", [320, 390])
async def test_mobile_inline_configuration_link(docs_page, width):
    await docs_page.set_viewport_size({"width": width, "height": 900})
    await docs_page.goto(f"{DOCS_URL}#quickstart")
    heading = docs_page.locator("h2[id='config']")
    link = docs_page.get_by_role("main").get_by_role(
        "link", name=await heading.text_content(), exact=True
    )
    await link.focus()
    await link.press("Enter")
    await assert_anchor_visible(docs_page, "config")


async def test_fragment_back_and_forward_keep_native_history(docs_page):
    await docs_page.goto(f"{DOCS_URL}#install")
    for anchor in ("config", "quickstart"):
        heading = docs_page.locator(f"h2[id='{anchor}']")
        await docs_page.get_by_role("navigation").get_by_role(
            "link", name=await heading.text_content(), exact=True
        ).click()
        await assert_anchor_visible(docs_page, anchor)
    await docs_page.go_back()
    await assert_anchor_visible(docs_page, "config")
    await docs_page.go_forward()
    await assert_anchor_visible(docs_page, "quickstart")
