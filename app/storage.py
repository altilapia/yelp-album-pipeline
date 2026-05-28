from __future__ import annotations

import json
from pathlib import Path

ALBUMS_FILE = Path(__file__).parent.parent / "data" / "albums.json"


def _load() -> list[str]:
    if not ALBUMS_FILE.exists():
        return []
    return json.loads(ALBUMS_FILE.read_text(encoding="utf-8"))


def _save(urls: list[str]) -> None:
    ALBUMS_FILE.parent.mkdir(exist_ok=True)
    ALBUMS_FILE.write_text(json.dumps(urls, indent=2), encoding="utf-8")


def get_albums() -> list[str]:
    return _load()


def add_album(url: str) -> None:
    urls = _load()
    if url not in urls:
        urls.append(url)
        _save(urls)


def remove_album(url: str) -> None:
    urls = _load()
    _save([u for u in urls if u != url])
