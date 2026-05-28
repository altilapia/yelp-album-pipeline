from __future__ import annotations

import time

from playwright.sync_api import Page, sync_playwright

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _scroll_until_stable(
    page: Page,
    *,
    scroll_pause: float = 3.0,
    max_unchanged: int = 5,
) -> None:
    """Scroll the last loaded item into view until the count stops growing."""
    prev_count = -1
    unchanged = 0
    while unchanged < max_unchanged:
        count = page.locator("li.collection-item").count()
        if count == prev_count:
            unchanged += 1
        else:
            unchanged = 0
            prev_count = count
        if count > 0:
            page.locator("li.collection-item").nth(count - 1).scroll_into_view_if_needed()
        else:
            page.evaluate("window.scrollBy(0, window.innerHeight)")
        time.sleep(scroll_pause)


def scrape_album(
    url: str,
    *,
    headless: bool = False,
    scroll_pause: float = 3.0,
    max_unchanged: int = 5,
) -> str:
    """Open a Yelp album URL, scroll until all businesses load, return full HTML.

    Run `playwright install chromium` once before calling this.
    headless=False (default) reduces bot-detection risk on Yelp.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=_USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()
        # Mask the webdriver flag even in non-headless mode
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page.goto(url, wait_until="networkidle", timeout=60_000)
        _scroll_until_stable(page, scroll_pause=scroll_pause, max_unchanged=max_unchanged)
        html = page.content()
        browser.close()
    return html
