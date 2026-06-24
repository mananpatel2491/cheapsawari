"""Allowlist store selection — resolves the active AllowedUserRepository.

Uses the same `WATCH_STORE` setting as the watch store so both live in one backend
(SQLite locally, Firestore in prod). Cached per process.
"""
from __future__ import annotations

from functools import lru_cache

from ..config import Settings, get_settings
from .base import AllowedUserRepository
from .sqlite_store import SqliteAllowedUserRepository


@lru_cache(maxsize=1)
def _build(store: str, sqlite_path: str, gcp_project: str | None) -> AllowedUserRepository:
    if store == "sqlite":
        return SqliteAllowedUserRepository(sqlite_path)
    if store == "firestore":
        from .firestore_store import FirestoreAllowedUserRepository

        return FirestoreAllowedUserRepository(project=gcp_project)
    raise ValueError(f"Unknown WATCH_STORE '{store}' (expected 'sqlite' or 'firestore').")


def get_user_repository(settings: Settings | None = None) -> AllowedUserRepository:
    """Return the configured AllowedUserRepository (default: SQLite)."""
    settings = settings or get_settings()
    return _build(settings.watch_store, settings.sqlite_path, settings.gcp_project)
