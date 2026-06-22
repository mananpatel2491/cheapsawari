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
def _build(store: str, sqlite_path: str) -> WatchRepository:
    if store == "sqlite":
        return SqliteWatchRepository(sqlite_path)
    if store == "firestore":
        # Wired at Slice 3 (cloud). Kept explicit so the seam is visible.
        raise NotImplementedError(
            "WATCH_STORE=firestore is reserved for Slice 3 (cloud). Use 'sqlite' for now."
        )
    raise ValueError(f"Unknown WATCH_STORE '{store}' (expected 'sqlite' or 'firestore').")


def get_repository(settings: Settings | None = None) -> WatchRepository:
    """Return the configured WatchRepository (default: SQLite)."""
    settings = settings or get_settings()
    return _build(settings.watch_store, settings.sqlite_path)
