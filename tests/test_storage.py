import pytest

import app.storage as storage_mod

URL = "https://www.yelp.com/collection/abc"
URL2 = "https://www.yelp.com/collection/xyz"


@pytest.fixture(autouse=True)
def tmp_albums_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_mod, "ALBUMS_FILE", tmp_path / "albums.json")


def _urls(albums):
    return [a["url"] for a in albums]


def test_get_albums_empty_before_any_add():
    assert storage_mod.get_albums() == []


def test_add_album_persists():
    storage_mod.add_album(URL)
    assert URL in _urls(storage_mod.get_albums())


def test_add_album_is_idempotent():
    storage_mod.add_album(URL)
    storage_mod.add_album(URL)
    assert _urls(storage_mod.get_albums()).count(URL) == 1


def test_add_multiple_albums():
    storage_mod.add_album(URL)
    storage_mod.add_album(URL2)
    assert len(storage_mod.get_albums()) == 2


def test_add_album_initialises_name_and_biz_urls():
    storage_mod.add_album(URL)
    album = storage_mod.get_albums()[0]
    assert album["name"] == ""
    assert album["biz_urls"] == []


def test_remove_album():
    storage_mod.add_album(URL)
    storage_mod.remove_album(URL)
    assert URL not in _urls(storage_mod.get_albums())


def test_remove_nonexistent_album_is_safe():
    storage_mod.remove_album("https://www.yelp.com/collection/nope")
    assert storage_mod.get_albums() == []


def test_get_album_returns_dict():
    storage_mod.add_album(URL)
    album = storage_mod.get_album(URL)
    assert album is not None
    assert album["url"] == URL


def test_get_album_returns_none_for_missing():
    assert storage_mod.get_album(URL) is None


def test_update_album_name():
    storage_mod.add_album(URL)
    storage_mod.update_album(URL, name="Want to Go")
    assert storage_mod.get_album(URL)["name"] == "Want to Go"


def test_update_album_biz_urls():
    storage_mod.add_album(URL)
    biz_urls = ["https://www.yelp.com/biz/foo", "https://www.yelp.com/biz/bar"]
    storage_mod.update_album(URL, biz_urls=biz_urls)
    assert storage_mod.get_album(URL)["biz_urls"] == biz_urls


def test_update_album_unknown_url_is_safe():
    storage_mod.update_album("https://www.yelp.com/collection/missing", name="x")


def test_backward_compat_with_old_string_format(tmp_path, monkeypatch):
    import json
    f = tmp_path / "albums.json"
    f.write_text(json.dumps([URL, URL2]), encoding="utf-8")
    monkeypatch.setattr(storage_mod, "ALBUMS_FILE", f)
    albums = storage_mod.get_albums()
    assert len(albums) == 2
    assert albums[0]["url"] == URL
    assert albums[0]["name"] == ""
    assert albums[0]["biz_urls"] == []
