from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ALBUMS_FILE = Path(__file__).parent.parent / "data" / "albums.json"


def _load() -> list[dict]:
    if not ALBUMS_FILE.exists():
        return []
    raw = json.loads(ALBUMS_FILE.read_text(encoding="utf-8"))
    # Backward compat: old format was list[str]
    if raw and isinstance(raw[0], str):
        return [{"url": u, "name": "", "biz_urls": []} for u in raw]
    return raw


def _save(albums: list[dict]) -> None:
    ALBUMS_FILE.parent.mkdir(exist_ok=True)
    ALBUMS_FILE.write_text(json.dumps(albums, indent=2), encoding="utf-8")


def get_albums() -> list[dict]:
    return _load()


def get_album(url: str) -> Optional[dict]:
    for album in _load():
        if album["url"] == url:
            return album
    return None


def add_album(url: str) -> None:
    albums = _load()
    if not any(a["url"] == url for a in albums):
        albums.append({"url": url, "name": "", "biz_urls": []})
        _save(albums)


def update_album(url: str, *, name: Optional[str] = None, biz_urls: Optional[list] = None) -> None:
    albums = _load()
    for album in albums:
        if album["url"] == url:
            if name is not None:
                album["name"] = name
            if biz_urls is not None:
                album["biz_urls"] = biz_urls
            break
    _save(albums)


def remove_album(url: str) -> None:
    albums = _load()
    _save([a for a in albums if a["url"] != url])
