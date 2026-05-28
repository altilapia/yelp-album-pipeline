from unittest.mock import patch

from app.pipeline import run_pipeline

URL = "https://www.yelp.com/collection/V14fnCAwtDkPA5DFRkm7Nw"
FAKE_HTML = "<html>album</html>"
FAKE_BUSINESSES = [{"name": "Mott 32", "biz_url": "https://www.yelp.com/biz/mott-32-las-vegas-2"}]
FAKE_RESULT = {"new": 1, "updated": 0}
FAKE_NAME = "Want to Go"


def test_calls_scraper_with_url():
    with (
        patch("app.pipeline.scrape_album", return_value=FAKE_HTML) as mock_scrape,
        patch("app.pipeline.parse_album", return_value=FAKE_BUSINESSES),
        patch("app.pipeline.parse_album_name", return_value=FAKE_NAME),
        patch("app.pipeline.storage"),
        patch("app.pipeline.upload", return_value=FAKE_RESULT),
    ):
        run_pipeline(URL)
    mock_scrape.assert_called_once_with(URL)


def test_passes_html_to_parser():
    with (
        patch("app.pipeline.scrape_album", return_value=FAKE_HTML),
        patch("app.pipeline.parse_album", return_value=FAKE_BUSINESSES) as mock_parse,
        patch("app.pipeline.parse_album_name", return_value=FAKE_NAME),
        patch("app.pipeline.storage"),
        patch("app.pipeline.upload", return_value=FAKE_RESULT),
    ):
        run_pipeline(URL)
    mock_parse.assert_called_once_with(FAKE_HTML)


def test_passes_businesses_to_uploader():
    with (
        patch("app.pipeline.scrape_album", return_value=FAKE_HTML),
        patch("app.pipeline.parse_album", return_value=FAKE_BUSINESSES),
        patch("app.pipeline.parse_album_name", return_value=FAKE_NAME),
        patch("app.pipeline.storage"),
        patch("app.pipeline.upload", return_value=FAKE_RESULT) as mock_upload,
    ):
        run_pipeline(URL)
    mock_upload.assert_called_once_with(FAKE_BUSINESSES)


def test_returns_upload_result():
    with (
        patch("app.pipeline.scrape_album", return_value=FAKE_HTML),
        patch("app.pipeline.parse_album", return_value=FAKE_BUSINESSES),
        patch("app.pipeline.parse_album_name", return_value=FAKE_NAME),
        patch("app.pipeline.storage"),
        patch("app.pipeline.upload", return_value=FAKE_RESULT),
    ):
        result = run_pipeline(URL)
    assert result == FAKE_RESULT


def test_updates_storage_with_name_and_biz_urls():
    with (
        patch("app.pipeline.scrape_album", return_value=FAKE_HTML),
        patch("app.pipeline.parse_album", return_value=FAKE_BUSINESSES),
        patch("app.pipeline.parse_album_name", return_value=FAKE_NAME),
        patch("app.pipeline.storage") as mock_storage,
        patch("app.pipeline.upload", return_value=FAKE_RESULT),
    ):
        run_pipeline(URL)
    mock_storage.update_album.assert_called_once_with(
        URL,
        name=FAKE_NAME,
        biz_urls=["https://www.yelp.com/biz/mott-32-las-vegas-2"],
    )


def test_stages_run_in_order():
    order = []
    with (
        patch("app.pipeline.scrape_album", side_effect=lambda u: order.append("scrape") or FAKE_HTML),
        patch("app.pipeline.parse_album", side_effect=lambda h: order.append("parse") or FAKE_BUSINESSES),
        patch("app.pipeline.parse_album_name", return_value=FAKE_NAME),
        patch("app.pipeline.storage"),
        patch("app.pipeline.upload", side_effect=lambda b: order.append("upload") or FAKE_RESULT),
    ):
        run_pipeline(URL)
    assert order == ["scrape", "parse", "upload"]
