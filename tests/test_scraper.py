from unittest.mock import MagicMock, call, patch

from app.scraper import _scroll_until_stable, scrape_album


def _page(counts):
    """Mock page whose locator().count() returns successive values."""
    page = MagicMock()
    page.locator.return_value.count.side_effect = counts
    return page


# ── _scroll_until_stable logic ────────────────────────────────────────────────

def test_stable_immediately_exits_after_max_unchanged():
    # count=10 on first call (resets from -1→10), then stable → 4 scroll_into_view calls
    page = _page([10, 10, 10, 10])
    _scroll_until_stable(page, scroll_pause=0, max_unchanged=3)
    assert page.locator.return_value.nth.return_value.scroll_into_view_if_needed.call_count == 4


def test_growing_count_resets_unchanged_counter():
    # 10→20 growth (2 resets), then stable 3 times → 5 scroll_into_view calls
    page = _page([10, 20, 20, 20, 20])
    _scroll_until_stable(page, scroll_pause=0, max_unchanged=3)
    assert page.locator.return_value.nth.return_value.scroll_into_view_if_needed.call_count == 5


def test_scroll_into_view_targets_last_item():
    page = _page([10, 10])
    _scroll_until_stable(page, scroll_pause=0, max_unchanged=1)
    page.locator.return_value.nth.assert_called_with(9)


def test_empty_page_falls_back_to_scroll_js():
    # count=0 on every call: falls back to window.scrollBy
    page = _page([0, 0, 0, 0])
    _scroll_until_stable(page, scroll_pause=0, max_unchanged=3)
    assert page.evaluate.call_count == 4
    for c in page.evaluate.call_args_list:
        assert "scrollBy" in c[0][0]
        assert "innerHeight" in c[0][0]


def test_max_unchanged_one_exits_quickly():
    page = _page([10, 10])
    _scroll_until_stable(page, scroll_pause=0, max_unchanged=1)
    assert page.locator.return_value.nth.return_value.scroll_into_view_if_needed.call_count == 2


# ── scrape_album browser setup ────────────────────────────────────────────────

def _mock_playwright(html="<html></html>"):
    """Return a patch target and a mock that simulates playwright context."""
    pw = MagicMock()
    page = MagicMock()
    page.content.return_value = html
    page.locator.return_value.count.return_value = 0

    browser = MagicMock()
    browser.new_context.return_value.__enter__ = MagicMock(return_value=MagicMock())
    context = MagicMock()
    context.new_page.return_value = page
    browser.new_context.return_value = context

    chromium = MagicMock()
    chromium.launch.return_value = browser
    pw.chromium = chromium
    pw.__enter__ = MagicMock(return_value=pw)
    pw.__exit__ = MagicMock(return_value=False)
    return pw


def test_scrape_album_returns_html():
    pw = _mock_playwright("<html>test</html>")
    with patch("app.scraper.sync_playwright", return_value=pw):
        result = scrape_album("https://www.yelp.com/collection/test", scroll_pause=0)
    assert result == "<html>test</html>"


def test_scrape_album_launches_non_headless_by_default():
    pw = _mock_playwright()
    with patch("app.scraper.sync_playwright", return_value=pw):
        scrape_album("https://www.yelp.com/collection/test", scroll_pause=0)
    pw.chromium.launch.assert_called_once_with(headless=False)


def test_scrape_album_headless_flag_forwarded():
    pw = _mock_playwright()
    with patch("app.scraper.sync_playwright", return_value=pw):
        scrape_album("https://www.yelp.com/collection/test", headless=True, scroll_pause=0)
    pw.chromium.launch.assert_called_once_with(headless=True)


def test_scrape_album_sets_user_agent():
    pw = _mock_playwright()
    with patch("app.scraper.sync_playwright", return_value=pw):
        scrape_album("https://www.yelp.com/collection/test", scroll_pause=0)
    ctx_kwargs = pw.chromium.launch.return_value.new_context.call_args[1]
    assert "Mozilla" in ctx_kwargs["user_agent"]
    assert "Chrome" in ctx_kwargs["user_agent"]


def test_scrape_album_injects_webdriver_mask():
    pw = _mock_playwright()
    page = pw.chromium.launch.return_value.new_context.return_value.new_page.return_value
    with patch("app.scraper.sync_playwright", return_value=pw):
        scrape_album("https://www.yelp.com/collection/test", scroll_pause=0)
    scripts = [c[0][0] for c in page.add_init_script.call_args_list]
    assert any("webdriver" in s for s in scripts)
