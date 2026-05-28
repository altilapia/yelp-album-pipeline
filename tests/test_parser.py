from pathlib import Path

import pytest

from app.parser import parse_album_file, parse_album_name

FIXTURE = Path(__file__).parent / "fixtures" / "sample_album.html"


@pytest.fixture(scope="module")
def businesses():
    return parse_album_file(FIXTURE)


def test_total_count(businesses):
    assert len(businesses) == 53


def test_all_have_required_fields(businesses):
    required = {"name", "biz_url", "category", "rating", "review_count", "price", "city", "state"}
    for biz in businesses:
        assert required == set(biz.keys())


def test_mott_32(businesses):
    biz = next(b for b in businesses if b["name"] == "Mott 32")
    assert biz["biz_url"] == "https://www.yelp.com/biz/mott-32-las-vegas-2"
    assert biz["rating"] == 4.0
    assert biz["review_count"] == 1575
    assert biz["price"] == "$$$$"
    assert "Chinese" in biz["category"]
    assert biz["city"] == "Las Vegas"
    assert biz["state"] == "NV"


def test_mura_japanese_bbq(businesses):
    biz = next(b for b in businesses if "Mura Japanese BBQ" in b["name"])
    assert biz["biz_url"] == "https://www.yelp.com/biz/mura-japanese-bbq-and-shabu-las-vegas-4"
    assert biz["rating"] == 4.5
    assert biz["review_count"] == 1045
    assert biz["price"] == "$$$"
    assert "Barbeque" in biz["category"]


def test_mango_mango_no_price(businesses):
    biz = next(b for b in businesses if b["name"] == "Mango Mango Dessert")
    assert biz["price"] is None
    assert biz["rating"] == 4.5
    assert biz["review_count"] == 803
    assert "Desserts" in biz["category"]


def test_biz_urls_are_absolute(businesses):
    for biz in businesses:
        assert biz["biz_url"].startswith("https://www.yelp.com/biz/")


def test_ratings_in_range(businesses):
    for biz in businesses:
        if biz["rating"] is not None:
            assert 1.0 <= biz["rating"] <= 5.0


def test_review_counts_positive(businesses):
    for biz in businesses:
        if biz["review_count"] is not None:
            assert biz["review_count"] > 0


def test_parse_album_name_from_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    name = parse_album_name(html)
    assert name == "Want to go"


def test_parse_album_name_empty_html():
    assert parse_album_name("<html></html>") == ""


def test_parse_album_name_falls_back_to_h1():
    html = "<html><head></head><body><h1>My List</h1></body></html>"
    assert parse_album_name(html) == "My List"


def test_parse_album_name_falls_back_to_title():
    html = "<html><head><title>My Album - Yelp</title></head><body></body></html>"
    assert parse_album_name(html) == "My Album"
