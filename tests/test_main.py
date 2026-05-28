from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

URL = "https://www.yelp.com/collection/V14fnCAwtDkPA5DFRkm7Nw"


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


def test_index_shows_tracked_albums(client):
    with patch("app.main.storage") as ms:
        ms.get_albums.return_value = [URL]
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


# ── lifespan ──────────────────────────────────────────────────────────────────

def test_lifespan_starts_and_stops_scheduler():
    mock_sched = MagicMock()
    with patch("app.main.create_scheduler", return_value=mock_sched):
        with TestClient(app):
            mock_sched.start.assert_called_once()
    mock_sched.shutdown.assert_called_once()
