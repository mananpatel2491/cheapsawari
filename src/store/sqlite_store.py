"""SQLite-backed WatchRepository.

Default store: stdlib `sqlite3` only (zero extra dependency), durable to a file,
and hermetic for tests. A connection is opened per operation (fine at personal
scale) with foreign keys enabled so deleting a watch cascades its snapshots.

Datetimes are stored as ISO-8601 UTC strings; dates as ISO date strings.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date as _date
from datetime import datetime, timezone

from ..models import Offer, PriceSnapshot, SnapshotLeg, TripLeg, Watch, WatchCreate
from .base import WatchNotFoundError, WatchRepository, build_snapshot


def _dump_legs(legs) -> str | None:
    """Serialize a list of TripLeg/SnapshotLeg to a JSON string (or None)."""
    return json.dumps([leg.model_dump(mode="json") for leg in legs]) if legs else None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watches (
    id             TEXT PRIMARY KEY,
    origin         TEXT NOT NULL,
    destination    TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    cabin          TEXT NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL,
    trip_type        TEXT NOT NULL DEFAULT 'one_way',
    return_date      TEXT,
    depart_flex_days INTEGER NOT NULL DEFAULT 0,
    return_flex_days INTEGER NOT NULL DEFAULT 0,
    owner_email      TEXT,
    legs_json        TEXT
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
    outbound_price REAL,
    outbound_date  TEXT,
    return_price   REAL,
    return_date    TEXT,
    legs_json      TEXT,
    FOREIGN KEY (watch_id) REFERENCES watches(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_snapshots_watch ON snapshots(watch_id, observed_at);
"""

# Slice 7 added columns; ADD them to pre-existing tables (SQLite has no ADD COLUMN
# IF NOT EXISTS, so we diff against pragma table_info). Each is nullable / has a
# default, so existing rows migrate cleanly.
_MIGRATIONS = {
    "watches": [
        ("trip_type", "TEXT NOT NULL DEFAULT 'one_way'"),
        ("return_date", "TEXT"),
        ("depart_flex_days", "INTEGER NOT NULL DEFAULT 0"),
        ("return_flex_days", "INTEGER NOT NULL DEFAULT 0"),
        ("owner_email", "TEXT"),  # Slice 8 — per-user ownership
        ("legs_json", "TEXT"),    # Slice 9 — multi-city legs
    ],
    "snapshots": [
        ("outbound_price", "REAL"),
        ("outbound_date", "TEXT"),
        ("return_price", "REAL"),
        ("return_date", "TEXT"),
        ("legs_json", "TEXT"),    # Slice 9 — per-leg breakdown
    ],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SqliteWatchRepository(WatchRepository):
    def __init__(self, path: str) -> None:
        self._path = path
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            self._migrate(conn)

    @staticmethod
    def _migrate(conn) -> None:
        """Bring a pre-Slice-7 table up to date by adding any missing columns."""
        for table, columns in _MIGRATIONS.items():
            existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for name, ddl in columns:
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")

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
            trip_type=row["trip_type"],
            return_date=_date.fromisoformat(row["return_date"]) if row["return_date"] else None,
            depart_flex_days=row["depart_flex_days"],
            return_flex_days=row["return_flex_days"],
            owner_email=row["owner_email"],
            legs=[TripLeg(**d) for d in json.loads(row["legs_json"])] if row["legs_json"] else None,
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
            outbound_price=row["outbound_price"],
            outbound_date=_date.fromisoformat(row["outbound_date"]) if row["outbound_date"] else None,
            return_price=row["return_price"],
            return_date=_date.fromisoformat(row["return_date"]) if row["return_date"] else None,
            legs=[SnapshotLeg(**d) for d in json.loads(row["legs_json"])] if row["legs_json"] else None,
        )

    # --- watches ------------------------------------------------------------
    def create_watch(self, data: WatchCreate, owner_email: str | None = None) -> Watch:
        watch = Watch(
            id=str(uuid.uuid4()),
            origin=data.origin.upper(),
            destination=data.destination.upper(),
            departure_date=data.departure_date,
            cabin=data.cabin.upper(),
            active=True,
            created_at=_now(),
            trip_type=data.trip_type,
            return_date=data.return_date,
            depart_flex_days=data.depart_flex_days,
            return_flex_days=data.return_flex_days,
            owner_email=owner_email,
            legs=data.legs,
        )
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO watches (id, origin, destination, departure_date, cabin, active, "
                "created_at, trip_type, return_date, depart_flex_days, return_flex_days, owner_email, legs_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    watch.id,
                    watch.origin,
                    watch.destination,
                    watch.departure_date.isoformat(),
                    watch.cabin,
                    int(watch.active),
                    watch.created_at.isoformat(),
                    watch.trip_type,
                    watch.return_date.isoformat() if watch.return_date else None,
                    watch.depart_flex_days,
                    watch.return_flex_days,
                    watch.owner_email,
                    _dump_legs(watch.legs),
                ),
            )
        return watch

    def get_watch(self, watch_id: str) -> Watch | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
        return self._row_to_watch(row) if row else None

    def update_watch(self, watch_id: str, data: WatchCreate) -> Watch:
        existing = self.get_watch(watch_id)
        if existing is None:
            raise WatchNotFoundError(watch_id)
        # Rebuild from the validated input but keep identity + lifecycle.
        updated = Watch(
            id=existing.id,
            origin=data.origin.upper(),
            destination=data.destination.upper(),
            departure_date=data.departure_date,
            cabin=data.cabin.upper(),
            active=existing.active,
            created_at=existing.created_at,
            trip_type=data.trip_type,
            return_date=data.return_date,
            depart_flex_days=data.depart_flex_days,
            return_flex_days=data.return_flex_days,
            owner_email=existing.owner_email,
            legs=data.legs,
        )
        with self._conn() as conn:
            conn.execute(
                "UPDATE watches SET origin = ?, destination = ?, departure_date = ?, cabin = ?, "
                "trip_type = ?, return_date = ?, depart_flex_days = ?, return_flex_days = ?, legs_json = ? "
                "WHERE id = ?",
                (
                    updated.origin,
                    updated.destination,
                    updated.departure_date.isoformat(),
                    updated.cabin,
                    updated.trip_type,
                    updated.return_date.isoformat() if updated.return_date else None,
                    updated.depart_flex_days,
                    updated.return_flex_days,
                    _dump_legs(updated.legs),
                    updated.id,
                ),
            )
        return updated

    def list_watches(self, active_only: bool = False, owner_email: str | None = None) -> list[Watch]:
        clauses, params = [], []
        if active_only:
            clauses.append("active = 1")
        if owner_email is not None:
            clauses.append("owner_email = ?")
            params.append(owner_email)
        query = "SELECT * FROM watches"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_watch(r) for r in rows]

    def delete_watch(self, watch_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM watches WHERE id = ?", (watch_id,))
        return cur.rowcount > 0

    # --- snapshots ----------------------------------------------------------
    def add_snapshot(
        self,
        watch_id: str,
        legs: list[Offer],
        *,
        total: float | None = None,
        trip_type: str = "one_way",
    ) -> PriceSnapshot:
        if self.get_watch(watch_id) is None:
            raise WatchNotFoundError(watch_id)
        snap = build_snapshot(watch_id, legs, total=total, trip_type=trip_type)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO snapshots (id, watch_id, price, currency, cabin, fare_basis, carrier, "
                "provider, observed_at, outbound_price, outbound_date, return_price, return_date, legs_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    snap.outbound_price,
                    snap.outbound_date.isoformat() if snap.outbound_date else None,
                    snap.return_price,
                    snap.return_date.isoformat() if snap.return_date else None,
                    _dump_legs(snap.legs),
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
