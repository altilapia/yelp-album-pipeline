from app.parser import parse_album
from app.scraper import scrape_album
from app.sheets import upload


def run_pipeline(url: str) -> dict:
    """Scrape a Yelp album URL, parse businesses, upsert to Google Sheet.

    Returns the upload result: {'new': int, 'updated': int}.
    """
    html = scrape_album(url)
    businesses = parse_album(html)
    return upload(businesses)
