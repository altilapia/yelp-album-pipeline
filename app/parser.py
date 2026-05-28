from __future__ import annotations

from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup


def parse_album(html: str) -> list[dict]:
    """Parse rendered Yelp album HTML and return a list of business dicts."""
    soup = BeautifulSoup(html, "lxml")
    results = []

    for item in soup.select("li.collection-item"):
        name_tag = item.select_one("a.biz-name")
        if not name_tag:
            continue

        name = name_tag.get_text(strip=True)
        biz_url = name_tag.get("href", "")

        rating_meta = item.select_one("meta[itemprop='ratingValue']")
        rating: Optional[float] = (
            float(rating_meta["content"]) if rating_meta else None
        )

        review_tag = item.select_one("span[itemprop='reviewCount']")
        review_count: Optional[int] = (
            int(review_tag.get_text(strip=True)) if review_tag else None
        )

        price_tag = item.select_one("span.business-attribute.price-range")
        price: Optional[str] = price_tag.get_text(strip=True) if price_tag else None

        category_tags = item.select("span.category-str-list a")
        category = ", ".join(t.get_text(strip=True) for t in category_tags)

        neighborhood_tag = item.select_one("span.addr-city")
        neighborhood_text = neighborhood_tag.get_text(strip=True) if neighborhood_tag else ""
        if ", " in neighborhood_text:
            city, state = neighborhood_text.rsplit(", ", 1)
        else:
            city, state = neighborhood_text or None, None

        results.append(
            {
                "name": name,
                "biz_url": ("https://www.yelp.com" + biz_url) if biz_url.startswith("/") else biz_url,
                "category": category,
                "rating": rating,
                "review_count": review_count,
                "price": price,
                "city": city or None,
                "state": state or None,
            }
        )

    return results


def parse_album_file(path: str | Path) -> list[dict]:
    return parse_album(Path(path).read_text(encoding="utf-8"))
