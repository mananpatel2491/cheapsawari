"""Store selection — resolves the active WatchRepository from settings.

Cached so the SQLite schema is initialized once per process and the same
repository instance is reused across requests.
"""
from __future__ import annotations

from functools import lru_cache

from ..config import Settings, get_settings
from .base import WatchRepository
from .sqlite_store import SqliteWatchRepository


@lru_cache(maxsize=1)
def _build(store: str, sqlite_path: str, gcp_project: str | None) -> WatchRepository:
    if store == "sqlite":
        return SqliteWatchRepository(sqlite_path)
    if store == "firestore":
        # Imported lazily so local/sqlite runs don't require the Firestore client.
        from .firestore_store import FirestoreWatchRepository

        return FirestoreWatchRepository(project=gcp_project)
    raise ValueError(f"Unknown WATCH_STORE '{store}' (expected 'sqlite' or 'firestore').")


def get_repository(settings: Settings | None = None) -> WatchRepository:
    """Return the configured WatchRepository (default: SQLite)."""
    settings = settings or get_settings()
    return _build(settings.watch_store, settings.sqlite_path, settings.gcp_project)
