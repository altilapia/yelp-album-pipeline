import pytest
import app.database as db_mod


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Redirect all DB operations to a per-test temporary SQLite file."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(db_mod, "_LEGACY_JSON", tmp_path / "nonexistent.json")
    db_mod.init_db()
