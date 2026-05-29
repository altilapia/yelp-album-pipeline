from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.database import get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_albums() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT url, name FROM albums ORDER BY added_at").fetchall()
        result = []
        for row in rows:
            biz_urls = [
                r[0] for r in conn.execute(
                    "SELECT biz_url FROM album_businesses WHERE album_url = ? ORDER BY rowid",
                    (row["url"],),
                ).fetchall()
            ]
            result.append({"url": row["url"], "name": row["name"], "biz_urls": biz_urls})
        return result


def get_album(url: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT url, name FROM albums WHERE url = ?", (url,)).fetchone()
        if not row:
            return None
        biz_urls = [
            r[0] for r in conn.execute(
                "SELECT biz_url FROM album_businesses WHERE album_url = ? ORDER BY rowid",
                (url,),
            ).fetchall()
        ]
        return {"url": row["url"], "name": row["name"], "biz_urls": biz_urls}


def add_album(url: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO albums (url, name, added_at) VALUES (?, '', ?)",
            (url, _now()),
        )


def update_album(url: str, *, name: Optional[str] = None, biz_urls: Optional[list] = None) -> None:
    with get_conn() as conn:
        if name is not None:
            conn.execute("UPDATE albums SET name = ? WHERE url = ?", (name, url))
        if biz_urls is not None:
            conn.execute("DELETE FROM album_businesses WHERE album_url = ?", (url,))
            if biz_urls:
                conn.executemany(
                    "INSERT OR IGNORE INTO album_businesses (album_url, biz_url) VALUES (?, ?)",
                    [(url, b) for b in biz_urls],
                )


def remove_album(url: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM album_businesses WHERE album_url = ?", (url,))
        conn.execute("DELETE FROM albums WHERE url = ?", (url,))


def upsert_businesses(album_url: str, businesses: list[dict]) -> dict:
    """Upsert current businesses into the DB; return {'new': [...], 'removed': [...]} biz_urls."""
    now = _now()
    with get_conn() as conn:
        existing = {
            row[0] for row in conn.execute(
                "SELECT biz_url FROM album_businesses WHERE album_url = ?", (album_url,)
            ).fetchall()
        }
        incoming = {b["biz_url"] for b in businesses}

        for biz in businesses:
            conn.execute(
                """
                INSERT INTO businesses
                    (biz_url, name, category, rating, review_count, price, city, state,
                     first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(biz_url) DO UPDATE SET
                    name=excluded.name,
                    category=excluded.category,
                    rating=excluded.rating,
                    review_count=excluded.review_count,
                    price=excluded.price,
                    city=excluded.city,
                    state=excluded.state,
                    last_seen=excluded.last_seen
                """,
                (
                    biz["biz_url"], biz.get("name"), biz.get("category"),
                    biz.get("rating"), biz.get("review_count"), biz.get("price"),
                    biz.get("city"), biz.get("state"),
                    now, now,
                ),
            )

        return {
            "new": sorted(incoming - existing),
            "removed": sorted(existing - incoming),
        }


def record_snapshot(album_url: str, businesses: list[dict], run_at: str) -> None:
    """Append one snapshot row per business for the given run timestamp."""
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO snapshots
                (run_at, album_url, biz_url, name, category, rating, review_count,
                 price, city, state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_at, album_url, b["biz_url"], b.get("name"), b.get("category"),
                    b.get("rating"), b.get("review_count"), b.get("price"),
                    b.get("city"), b.get("state"),
                )
                for b in businesses
            ],
        )


def get_stats() -> dict:
    with get_conn() as conn:
        run_count = conn.execute(
            "SELECT COUNT(DISTINCT run_at) FROM snapshots"
        ).fetchone()[0]

        total_businesses = conn.execute(
            "SELECT COUNT(DISTINCT b.biz_url) FROM businesses b "
            "JOIN album_businesses ab ON b.biz_url = ab.biz_url"
        ).fetchone()[0]

        # Top 10 most recently added businesses (added after the very first scrape)
        new_businesses = [dict(row) for row in conn.execute("""
            SELECT b.name, b.biz_url, b.category, b.rating, b.review_count,
                   b.city, b.state, b.first_seen,
                   GROUP_CONCAT(a.name, ', ') AS album_names
            FROM businesses b
            JOIN album_businesses ab ON b.biz_url = ab.biz_url
            JOIN albums a ON ab.album_url = a.url
            WHERE b.first_seen > (SELECT MIN(first_seen) FROM businesses)
            GROUP BY b.biz_url
            ORDER BY b.first_seen DESC, b.name
            LIMIT 10
        """).fetchall()]

        # Most reviewed business per album
        most_reviewed_per_album = [dict(row) for row in conn.execute("""
            SELECT album_name, name, biz_url, category, review_count, rating, city
            FROM (
                SELECT a.name AS album_name, b.name, b.biz_url, b.category,
                       b.review_count, b.rating, b.city,
                       ROW_NUMBER() OVER (
                           PARTITION BY ab.album_url ORDER BY b.review_count DESC
                       ) AS rn
                FROM businesses b
                JOIN album_businesses ab ON b.biz_url = ab.biz_url
                JOIN albums a ON ab.album_url = a.url
                WHERE b.review_count IS NOT NULL
            )
            WHERE rn = 1
            ORDER BY album_name
        """).fetchall()]

        # Top 5 review count increase between the two most recent runs
        top_review_growth = []
        if run_count >= 2:
            top_review_growth = [dict(row) for row in conn.execute("""
                WITH latest_run AS (SELECT MAX(run_at) AS run_at FROM snapshots),
                prev_run AS (
                    SELECT MAX(run_at) AS run_at FROM snapshots
                    WHERE run_at < (SELECT run_at FROM latest_run)
                ),
                latest AS (
                    SELECT s.biz_url, s.review_count
                    FROM snapshots s, latest_run lr WHERE s.run_at = lr.run_at
                ),
                prev AS (
                    SELECT s.biz_url, s.review_count
                    FROM snapshots s, prev_run pr WHERE s.run_at = pr.run_at
                )
                SELECT b.name, b.biz_url, b.category, b.rating, b.city,
                       l.review_count  AS current_reviews,
                       p.review_count  AS prev_reviews,
                       (l.review_count - p.review_count) AS review_increase,
                       GROUP_CONCAT(a.name, ', ') AS album_names
                FROM latest l
                JOIN prev p ON l.biz_url = p.biz_url
                JOIN businesses b ON b.biz_url = l.biz_url
                JOIN album_businesses ab ON b.biz_url = ab.biz_url
                JOIN albums a ON ab.album_url = a.url
                WHERE l.review_count > p.review_count
                GROUP BY l.biz_url
                ORDER BY review_increase DESC
                LIMIT 5
            """).fetchall()]

        # Top 10 primary categories by business count
        top_categories = [dict(row) for row in conn.execute("""
            SELECT
                TRIM(CASE WHEN INSTR(b.category, ',') > 0
                     THEN SUBSTR(b.category, 1, INSTR(b.category, ',') - 1)
                     ELSE b.category END) AS primary_category,
                COUNT(*) AS count
            FROM businesses b
            JOIN album_businesses ab ON b.biz_url = ab.biz_url
            WHERE b.category IS NOT NULL AND b.category != ''
            GROUP BY primary_category
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()]

        # Price tier distribution and average per album
        price_per_album = [dict(row) for row in conn.execute("""
            SELECT
                a.name AS album_name,
                SUM(CASE b.price WHEN '$'    THEN 1 ELSE 0 END) AS p1,
                SUM(CASE b.price WHEN '$$'   THEN 1 ELSE 0 END) AS p2,
                SUM(CASE b.price WHEN '$$$'  THEN 1 ELSE 0 END) AS p3,
                SUM(CASE b.price WHEN '$$$$' THEN 1 ELSE 0 END) AS p4,
                ROUND(AVG(CASE b.price
                    WHEN '$'    THEN 1 WHEN '$$'   THEN 2
                    WHEN '$$$'  THEN 3 WHEN '$$$$' THEN 4
                END), 1) AS avg_tier
            FROM businesses b
            JOIN album_businesses ab ON b.biz_url = ab.biz_url
            JOIN albums a ON ab.album_url = a.url
            GROUP BY ab.album_url
            ORDER BY a.name
        """).fetchall()]

        # Top 10 cities by total review count
        top_cities = [dict(row) for row in conn.execute("""
            SELECT
                b.city,
                b.state,
                SUM(b.review_count)         AS total_reviews,
                COUNT(*)                    AS business_count,
                ROUND(AVG(b.review_count))  AS avg_reviews
            FROM businesses b
            JOIN album_businesses ab ON b.biz_url = ab.biz_url
            WHERE b.city IS NOT NULL AND b.review_count IS NOT NULL
            GROUP BY b.city, b.state
            ORDER BY total_reviews DESC
            LIMIT 10
        """).fetchall()]

        return {
            "run_count": run_count,
            "total_businesses": total_businesses,
            "new_businesses": new_businesses,
            "most_reviewed_per_album": most_reviewed_per_album,
            "top_review_growth": top_review_growth,
            "top_categories": top_categories,
            "price_per_album": price_per_album,
            "top_cities": top_cities,
        }
