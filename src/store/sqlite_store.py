"""SQLite-backed WatchRepository.

Default store: stdlib `sqlite3` only (zero extra dependency), durable to a file,
and hermetic for tests. A connection is opened per operation (fine at personal
scale) with foreign keys enabled so deleting a watch cascades its snapshots.

Datetimes are stored as ISO-8601 UTC strings; dates as ISO date strings.
"""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date as _date
from datetime import datetime, timezone

from ..models import Offer, PriceSnapshot, Watch, WatchCreate
from .base import WatchNotFoundError, WatchRepository

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id             TEXT PRIMARY KEY,
    origin         TEXT NOT NULL,
    destination    TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    cabin          TEXT NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id          TEXT PRIMARY KEY,
    watch_id    TEXT NOT NULL,
    price       REAL NOT NULL,
    currency    TEXT NOT NULL,
    cabin       TEXT NOT NULL,
    fare_basis  TEXT,
    carrier     TEXT,
    provider    TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_snapshots_watch ON snapshots(watch_id, observed_at);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteWatchRepository(WatchRepository):
    def __init__(self, path: str) -> None:
        self._path = path
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- row -> model -------------------------------------------------------
    @staticmethod
    def _row_to_watch(row: sqlite3.Row) -> Watch:
        return Watch(
            id=row["id"],
            origin=row["origin"],
            destination=row["destination"],
            departure_date=_date.fromisoformat(row["departure_date"]),
            cabin=row["cabin"],
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> PriceSnapshot:
        return PriceSnapshot(
            id=row["id"],
            watch_id=row["watch_id"],
            price=row["price"],
            currency=row["currency"],
            cabin=row["cabin"],
            fare_basis=row["fare_basis"],
            carrier=row["carrier"],
            provider=row["provider"],
            observed_at=datetime.fromisoformat(row["observed_at"]),
        )

    # --- watches ------------------------------------------------------------
    def create_watch(self, data: WatchCreate) -> Watch:
        watch = Watch(
            id=str(uuid.uuid4()),
            origin=data.origin.upper(),
            destination=data.destination.upper(),
            departure_date=data.departure_date,
            cabin=data.cabin.upper(),
            active=True,
            created_at=_now(),
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO watches (id, origin, destination, departure_date, cabin, active, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    watch.id,
                    watch.origin,
                    watch.destination,
                    watch.departure_date.isoformat(),
                    watch.cabin,
                    int(watch.active),
                    watch.created_at.isoformat(),
                ),
            )
        return watch

    def get_watch(self, watch_id: str) -> Watch | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
        return self._row_to_watch(row) if row else None

    def list_watches(self, active_only: bool = False) -> list[Watch]:
        query = "SELECT * FROM watches"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query).fetchall()
        return [self._row_to_watch(r) for r in rows]

    def delete_watch(self, watch_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
        return cur.rowcount > 0

    # --- snapshots ----------------------------------------------------------
    def add_snapshot(self, watch_id: str, offer: Offer) -> PriceSnapshot:
        if self.get_watch(watch_id) is None:
            raise WatchNotFoundError(watch_id)
        snap = PriceSnapshot(
            id=str(uuid.uuid4()),
            watch_id=watch_id,
            price=offer.price,
            currency=offer.currency,
            cabin=offer.cabin,
            fare_basis=offer.fare_basis,
            carrier=offer.carrier,
            provider=offer.provider,
            observed_at=offer.observed_at,
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO snapshots (id, watch_id, price, currency, cabin, fare_basis, carrier, provider, observed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    snap.id,
                    snap.watch_id,
                    snap.price,
                    snap.currency,
                    snap.cabin,
                    snap.fare_basis,
                    snap.carrier,
                    snap.provider,
                    snap.observed_at.isoformat(),
                ),
            )
        return snap

    def list_snapshots(self, watch_id: str, limit: int = 100) -> list[PriceSnapshot]:
        if self.get_watch(watch_id) is None:
            raise WatchNotFoundError(watch_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM snapshots WHERE watch_id = ? ORDER BY observed_at DESC LIMIT ?",
                (watch_id, limit),
            ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]
