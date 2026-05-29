import app.storage as storage_mod
from app.database import get_conn

URL = "https://www.yelp.com/collection/abc"
URL2 = "https://www.yelp.com/collection/xyz"
BIZ1 = "https://www.yelp.com/biz/foo"
BIZ2 = "https://www.yelp.com/biz/bar"

FULL_BIZ = {
    "biz_url": BIZ1,
    "name": "Foo",
    "category": "Cafe",
    "rating": 4.5,
    "review_count": 100,
    "price": "$$",
    "city": "Irvine",
    "state": "CA",
}


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
    biz_urls = [BIZ1, BIZ2]
    storage_mod.update_album(URL, biz_urls=biz_urls)
    assert storage_mod.get_album(URL)["biz_urls"] == biz_urls


def test_update_album_unknown_url_is_safe():
    storage_mod.update_album("https://www.yelp.com/collection/missing", name="x")


# ── upsert_businesses ─────────────────────────────────────────────────────────

def test_upsert_businesses_reports_new():
    storage_mod.add_album(URL)
    changes = storage_mod.upsert_businesses(URL, [FULL_BIZ])
    assert BIZ1 in changes["new"]
    assert changes["removed"] == []


def test_upsert_businesses_reports_removed():
    storage_mod.add_album(URL)
    storage_mod.update_album(URL, biz_urls=[BIZ1, BIZ2])
    changes = storage_mod.upsert_businesses(URL, [FULL_BIZ])  # only BIZ1
    assert BIZ2 in changes["removed"]
    assert BIZ1 not in changes["removed"]


def test_upsert_businesses_no_changes_when_same():
    storage_mod.add_album(URL)
    storage_mod.upsert_businesses(URL, [FULL_BIZ])
    storage_mod.update_album(URL, biz_urls=[BIZ1])
    changes = storage_mod.upsert_businesses(URL, [FULL_BIZ])
    assert changes["new"] == []
    assert changes["removed"] == []


def test_upsert_businesses_preserves_first_seen():
    storage_mod.add_album(URL)
    storage_mod.upsert_businesses(URL, [FULL_BIZ])
    with get_conn() as conn:
        first = conn.execute(
            "SELECT first_seen FROM businesses WHERE biz_url = ?", (BIZ1,)
        ).fetchone()["first_seen"]

    storage_mod.upsert_businesses(URL, [FULL_BIZ])
    with get_conn() as conn:
        after = conn.execute(
            "SELECT first_seen FROM businesses WHERE biz_url = ?", (BIZ1,)
        ).fetchone()["first_seen"]

    assert first == after


# ── record_snapshot ───────────────────────────────────────────────────────────

def test_record_snapshot_inserts_rows():
    storage_mod.add_album(URL)
    storage_mod.record_snapshot(URL, [FULL_BIZ], "2024-01-01T00:00:00+00:00")
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    assert count == 1


def test_record_snapshot_multiple_runs_accumulate():
    storage_mod.add_album(URL)
    storage_mod.record_snapshot(URL, [FULL_BIZ], "2024-01-01T00:00:00+00:00")
    storage_mod.record_snapshot(URL, [FULL_BIZ], "2024-01-02T00:00:00+00:00")
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    assert count == 2
