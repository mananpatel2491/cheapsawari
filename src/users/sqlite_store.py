"""SQLite-backed AllowedUserRepository (default store; stdlib only)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from ..models import AllowedUser
from .base import AllowedUserRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS allowed_users (
    email    TEXT PRIMARY KEY,
    added_by TEXT NOT NULL,
    added_at TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteAllowedUserRepository(AllowedUserRepository):
    def __init__(self, path: str) -> None:
        self._path = path
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> AllowedUser:
        return AllowedUser(
            email=row["email"],
            added_by=row["added_by"],
            added_at=datetime.fromisoformat(row["added_at"]),
        )

    def list_users(self) -> list[AllowedUser]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM allowed_users ORDER BY added_at DESC"
            ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def is_allowed(self, email: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM allowed_users WHERE email = ?", (email.lower(),)
            ).fetchone()
        return row is not None

    def add_user(self, email: str, added_by: str) -> AllowedUser:
        user = AllowedUser(email=email.lower(), added_by=added_by.lower(), added_at=_now())
        with self._conn() as conn:
            # Idempotent upsert — re-granting refreshes who/when without erroring.
            conn.execute(
                "INSERT INTO allowed_users (email, added_by, added_at) VALUES (?, ?, ?) "
                "ON CONFLICT(email) DO UPDATE SET added_by = excluded.added_by, "
                "added_at = excluded.added_at",
                (user.email, user.added_by, user.added_at.isoformat()),
            )
        return user

    def remove_user(self, email: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM allowed_users WHERE email = ?", (email.lower(),))
        return cur.rowcount > 0
