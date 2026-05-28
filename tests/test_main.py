from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

URL = "https://www.yelp.com/collection/V14fnCAwtDkPA5DFRkm7Nw"
ALBUM = {"url": URL, "name": "Want to Go", "biz_urls": []}


@pytest.fixture
def client():
    mock_sched = MagicMock()
    with patch("app.main.create_scheduler", return_value=mock_sched):
        with TestClient(app) as c:
            yield c


# ── GET / ─────────────────────────────────────────────────────────────────────

def test_index_returns_200(client):
    with patch("app.main.storage") as ms:
        ms.get_albums.return_value = []
        response = client.get("/")
    assert response.status_code == 200


def test_index_contains_form(client):
    with patch("app.main.storage") as ms:
        ms.get_albums.return_value = []
        response = client.get("/")
    assert "<form" in response.text


def test_index_shows_tracked_album_name(client):
    with patch("app.main.storage") as ms:
        ms.get_albums.return_value = [ALBUM]
        response = client.get("/")
    assert "Want to Go" in response.text
    assert URL in response.text


def test_index_shows_url_when_name_is_empty(client):
    with patch("app.main.storage") as ms:
        ms.get_albums.return_value = [{"url": URL, "name": "", "biz_urls": []}]
        response = client.get("/")
    assert URL in response.text


def test_index_shows_empty_message_when_no_albums(client):
    with patch("app.main.storage") as ms:
        ms.get_albums.return_value = []
        response = client.get("/")
    assert "No albums tracked" in response.text


# ── POST /scrape ───────────────────────────────────────────────────────────────

def test_scrape_redirects_to_root(client):
    with patch("app.main.storage"), patch("app.main.run_pipeline"):
        response = client.post("/scrape", data={"yelp_url": URL}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_scrape_adds_url_to_storage(client):
    with patch("app.main.storage") as ms, patch("app.main.run_pipeline"):
        ms.get_albums.return_value = []
        client.post("/scrape", data={"yelp_url": URL}, follow_redirects=False)
    ms.add_album.assert_called_once_with(URL)


def test_scrape_triggers_pipeline_as_background_task(client):
    with patch("app.main.storage") as ms, patch("app.main.run_pipeline") as mock_pipeline:
        ms.get_albums.return_value = []
        client.post("/scrape", data={"yelp_url": URL})
    mock_pipeline.assert_called_once_with(URL)


def test_scrape_missing_url_returns_422(client):
    response = client.post("/scrape", data={})
    assert response.status_code == 422


# ── POST /refresh ──────────────────────────────────────────────────────────────

def test_refresh_redirects_to_root(client):
    with patch("app.main.run_pipeline"):
        response = client.post("/refresh", data={"yelp_url": URL}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_refresh_triggers_pipeline(client):
    with patch("app.main.run_pipeline") as mock_pipeline:
        client.post("/refresh", data={"yelp_url": URL})
    mock_pipeline.assert_called_once_with(URL)


def test_refresh_does_not_add_to_storage(client):
    with patch("app.main.storage") as ms, patch("app.main.run_pipeline"):
        client.post("/refresh", data={"yelp_url": URL})
    ms.add_album.assert_not_called()


# ── POST /remove ───────────────────────────────────────────────────────────────

def test_remove_redirects_to_root(client):
    with patch("app.main.storage") as ms, patch("app.main.sheets"):
        ms.get_album.return_value = {"url": URL, "name": "", "biz_urls": []}
        ms.get_albums.return_value = []
        response = client.post("/remove", data={"yelp_url": URL}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_remove_calls_storage_remove(client):
    with patch("app.main.storage") as ms, patch("app.main.sheets"):
        ms.get_album.return_value = {"url": URL, "name": "", "biz_urls": []}
        ms.get_albums.return_value = []
        client.post("/remove", data={"yelp_url": URL})
    ms.remove_album.assert_called_once_with(URL)


def test_remove_calls_sheet_cleanup_for_exclusive_biz_urls(client):
    biz_url = "https://www.yelp.com/biz/foo"
    with patch("app.main.storage") as ms, patch("app.main.sheets") as mock_sheets:
        ms.get_album.return_value = {"url": URL, "name": "", "biz_urls": [biz_url]}
        ms.get_albums.return_value = [{"url": URL, "name": "", "biz_urls": [biz_url]}]
        client.post("/remove", data={"yelp_url": URL})
    mock_sheets.remove_businesses.assert_called_once_with([biz_url])


def test_remove_skips_sheet_cleanup_when_no_biz_urls(client):
    with patch("app.main.storage") as ms, patch("app.main.sheets") as mock_sheets:
        ms.get_album.return_value = {"url": URL, "name": "", "biz_urls": []}
        ms.get_albums.return_value = []
        client.post("/remove", data={"yelp_url": URL})
    mock_sheets.remove_businesses.assert_not_called()


def test_remove_does_not_delete_biz_urls_shared_with_other_albums(client):
    shared_biz = "https://www.yelp.com/biz/shared"
    other_url = "https://www.yelp.com/collection/other"
    with patch("app.main.storage") as ms, patch("app.main.sheets") as mock_sheets:
        ms.get_album.return_value = {"url": URL, "name": "", "biz_urls": [shared_biz]}
        ms.get_albums.return_value = [
            {"url": URL, "name": "", "biz_urls": [shared_biz]},
            {"url": other_url, "name": "", "biz_urls": [shared_biz]},
        ]
        client.post("/remove", data={"yelp_url": URL})
    mock_sheets.remove_businesses.assert_not_called()


# ── lifespan ──────────────────────────────────────────────────────────────────

def test_lifespan_starts_and_stops_scheduler():
    mock_sched = MagicMock()
    with patch("app.main.create_scheduler", return_value=mock_sched):
        with TestClient(app):
            mock_sched.start.assert_called_once()
    mock_sched.shutdown.assert_called_once()
