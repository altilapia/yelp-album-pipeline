from datetime import datetime, timezone

from app import storage
from app.parser import parse_album, parse_album_name
from app.scraper import scrape_album
from app.sheets import upload


def run_pipeline(url: str) -> dict:
    """Scrape a Yelp album URL, parse businesses, upsert to SQLite and Google Sheet.

    Returns the upload result: {'new': int, 'updated': int}.
    """
    html = scrape_album(url)
    businesses = parse_album(html)
    name = parse_album_name(html)
    run_at = datetime.now(timezone.utc).isoformat()

    changes = storage.upsert_businesses(url, businesses)
    storage.update_album(url, name=name, biz_urls=[b["biz_url"] for b in businesses])
    storage.record_snapshot(url, businesses, run_at)
    _log_changes(url, changes)

    return upload(businesses)


def _log_changes(url: str, changes: dict) -> None:
    label = url.rstrip("/").split("/")[-1] or url
    new, removed = changes.get("new", []), changes.get("removed", [])
    if new:
        print(f"[pipeline] {label}: +{len(new)} new", flush=True)
        for b in new:
            print(f"  + {b}", flush=True)
    if removed:
        print(f"[pipeline] {label}: -{len(removed)} removed", flush=True)
        for b in removed:
            print(f"  - {b}", flush=True)
    if not new and not removed:
        print(f"[pipeline] {label}: no changes", flush=True)
