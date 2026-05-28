from unittest.mock import MagicMock, call, patch

from app.pipeline import run_pipeline

URL = "https://www.yelp.com/collection/V14fnCAwtDkPA5DFRkm7Nw"
FAKE_HTML = "<html>album</html>"
FAKE_BUSINESSES = [{"name": "Mott 32", "biz_url": "https://www.yelp.com/biz/mott-32-las-vegas-2"}]
FAKE_RESULT = {"new": 1, "updated": 0}


def _patches():
    return (
        patch("app.pipeline.scrape_album", return_value=FAKE_HTML),
        patch("app.pipeline.parse_album", return_value=FAKE_BUSINESSES),
        patch("app.pipeline.upload", return_value=FAKE_RESULT),
    )


def test_calls_scraper_with_url():
    with _patches()[0] as mock_scrape, _patches()[1], _patches()[2]:
        run_pipeline(URL)
    mock_scrape.assert_called_once_with(URL)


def test_passes_html_to_parser():
    with _patches()[0], _patches()[1] as mock_parse, _patches()[2]:
        run_pipeline(URL)
    mock_parse.assert_called_once_with(FAKE_HTML)


def test_passes_businesses_to_uploader():
    with _patches()[0], _patches()[1], _patches()[2] as mock_upload:
        run_pipeline(URL)
    mock_upload.assert_called_once_with(FAKE_BUSINESSES)


def test_returns_upload_result():
    with _patches()[0], _patches()[1], _patches()[2]:
        result = run_pipeline(URL)
    assert result == FAKE_RESULT


def test_stages_run_in_order():
    order = []
    with (
        patch("app.pipeline.scrape_album", side_effect=lambda u: order.append("scrape") or FAKE_HTML),
        patch("app.pipeline.parse_album", side_effect=lambda h: order.append("parse") or FAKE_BUSINESSES),
        patch("app.pipeline.upload", side_effect=lambda b: order.append("upload") or FAKE_RESULT),
    ):
        run_pipeline(URL)
    assert order == ["scrape", "parse", "upload"]
