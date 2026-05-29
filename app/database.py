from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "yelp_albums.db"
_LEGACY_JSON = Path(__file__).parent.parent / "data" / "albums.json"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS albums (
                url      TEXT PRIMARY KEY,
                name     TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                biz_url      TEXT PRIMARY KEY,
                name         TEXT,
                category     TEXT,
                rating       REAL,
                review_count INTEGER,
                price        TEXT,
                city         TEXT,
                state        TEXT,
                first_seen   TEXT NOT NULL,
                last_seen    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS album_businesses (
                album_url TEXT NOT NULL,
                biz_url   TEXT NOT NULL,
                PRIMARY KEY (album_url, biz_url),
                FOREIGN KEY (album_url) REFERENCES albums(url) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at       TEXT NOT NULL,
                album_url    TEXT NOT NULL,
                biz_url      TEXT NOT NULL,
                name         TEXT,
                category     TEXT,
                rating       REAL,
                review_count INTEGER,
                price        TEXT,
                city         TEXT,
                state        TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_biz_url ON snapshots(biz_url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_run_at  ON snapshots(run_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_album   ON snapshots(album_url)")
    _migrate_from_json()


def _migrate_from_json() -> None:
    """One-time import of albums.json into SQLite if the DB albums table is still empty."""
    if not _LEGACY_JSON.exists():
        return
    with get_conn() as conn:
        if conn.execute("SELECT COUNT(*) FROM albums").fetchone()[0] > 0:
            return
        try:
            raw = json.loads(_LEGACY_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        now = datetime.now(timezone.utc).isoformat()
        if raw and isinstance(raw[0], str):
            raw = [{"url": u, "name": "", "biz_urls": []} for u in raw]

        for album in raw:
            url = album.get("url", "")
            if not url:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO albums (url, name, added_at) VALUES (?, ?, ?)",
                (url, album.get("name", ""), now),
            )
            conn.executemany(
                "INSERT OR IGNORE INTO album_businesses (album_url, biz_url) VALUES (?, ?)",
                [(url, b) for b in album.get("biz_urls", [])],
            )
        print(f"[database] migrated {len(raw)} album(s) from albums.json", flush=True)
