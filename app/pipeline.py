from app import storage
from app.parser import parse_album, parse_album_name
from app.scraper import scrape_album
from app.sheets import upload


def run_pipeline(url: str) -> dict:
    """Scrape a Yelp album URL, parse businesses, upsert to Google Sheet.

    Returns the upload result: {'new': int, 'updated': int}.
    """
    html = scrape_album(url)
    businesses = parse_album(html)
    name = parse_album_name(html)
    storage.update_album(url, name=name, biz_urls=[b["biz_url"] for b in businesses])
    return upload(businesses)
