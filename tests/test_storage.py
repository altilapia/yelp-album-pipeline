import pytest

import app.storage as storage_mod


@pytest.fixture(autouse=True)
def tmp_albums_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_mod, "ALBUMS_FILE", tmp_path / "albums.json")


def test_get_albums_empty_before_any_add():
    assert storage_mod.get_albums() == []


def test_add_album_persists():
    storage_mod.add_album("https://www.yelp.com/collection/abc")
    assert "https://www.yelp.com/collection/abc" in storage_mod.get_albums()


def test_add_album_is_idempotent():
    url = "https://www.yelp.com/collection/abc"
    storage_mod.add_album(url)
    storage_mod.add_album(url)
    assert storage_mod.get_albums().count(url) == 1


def test_add_multiple_albums():
    storage_mod.add_album("https://www.yelp.com/collection/one")
    storage_mod.add_album("https://www.yelp.com/collection/two")
    albums = storage_mod.get_albums()
    assert len(albums) == 2


def test_remove_album():
    url = "https://www.yelp.com/collection/abc"
    storage_mod.add_album(url)
    storage_mod.remove_album(url)
    assert url not in storage_mod.get_albums()


def test_remove_nonexistent_album_is_safe():
    storage_mod.remove_album("https://www.yelp.com/collection/nope")
    assert storage_mod.get_albums() == []
