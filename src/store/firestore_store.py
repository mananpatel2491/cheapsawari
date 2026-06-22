"""Firestore-backed WatchRepository — the cloud store (Slice 3b).

Same contract as the SQLite store, backed by Cloud Firestore so data survives
Cloud Run's ephemeral filesystem. Layout:

    watches/{watch_id}                      -> watch document
    watches/{watch_id}/snapshots/{snap_id}  -> price snapshots (subcollection)

Notes:
- Firestore does NOT cascade-delete subcollections, so delete_watch() removes a
  watch's snapshots explicitly before deleting the watch doc.
- list_watches() sorts/filters in Python (personal scale = few watches), which
  avoids needing a composite index for the active+created_at query.
- Dates have no native Firestore type, so departure_date is stored as an ISO
  string; datetimes use native timestamps.
"""
from __future__ import annotations

import uuid
from datetime import date as _date
from datetime import datetime, timezone

from google.cloud import firestore

from ..models import Offer, PriceSnapshot, Watch, WatchCreate
from .base import WatchNotFoundError, WatchRepository

_WATCHES = "watches"
_SNAPSHOTS = "snapshots"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value) -> datetime:
    """Firestore returns tz-aware datetimes (often DatetimeWithNanoseconds). Normalize."""
    if isinstance(value, datetime):
        return value
    # Defensive: if stored as ISO string somewhere.
    return datetime.fromisoformat(str(value))


class FirestoreWatchRepository(WatchRepository):
    def __init__(self, project: str | None = None) -> None:
        # project=None lets the client infer from ADC / the Cloud Run metadata server.
        self._db = firestore.Client(project=project) if project else firestore.Client()

    # --- doc -> model -------------------------------------------------------
    @staticmethod
    def _to_watch(doc) -> Watch:
        d = doc.to_dict()
        return Watch(
            id=doc.id,
            origin=d["origin"],
            destination=d["destination"],
            departure_date=_date.fromisoformat(d["departure_date"]),
            cabin=d["cabin"],
            active=bool(d.get("active", True)),
            created_at=_as_utc(d["created_at"]),
        )

    @staticmethod
    def _to_snapshot(doc, watch_id: str) -> PriceSnapshot:
        d = doc.to_dict()
        return PriceSnapshot(
            id=doc.id,
            watch_id=watch_id,
            price=d["price"],
            currency=d["currency"],
            cabin=d["cabin"],
            fare_basis=d.get("fare_basis"),
            carrier=d.get("carrier"),
            provider=d["provider"],
            observed_at=_as_utc(d["observed_at"]),
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
        self._db.collection(_WATCHES).document(watch.id).set(
            {
                "origin": watch.origin,
                "destination": watch.destination,
                "departure_date": watch.departure_date.isoformat(),
                "cabin": watch.cabin,
                "active": watch.active,
                "created_at": watch.created_at,
            }
        )
        return watch

    def get_watch(self, watch_id: str) -> Watch | None:
        doc = self._db.collection(_WATCHES).document(watch_id).get()
        return self._to_watch(doc) if doc.exists else None

    def list_watches(self, active_only: bool = False) -> list[Watch]:
        docs = self._db.collection(_WATCHES).stream()
        watches = [self._to_watch(d) for d in docs]
        if active_only:
            watches = [w for w in watches if w.active]
        watches.sort(key=lambda w: w.created_at, reverse=True)
        return watches

    def delete_watch(self, watch_id: str) -> bool:
        ref = self._db.collection(_WATCHES).document(watch_id)
        if not ref.get().exists:
            return False
        # Firestore has no cascade — delete the snapshots subcollection first.
        for snap in ref.collection(_SNAPSHOTS).stream():
            snap.reference.delete()
        ref.delete()
        return True

    # --- snapshots ----------------------------------------------------------
    def add_snapshot(self, watch_id: str, offer: Offer) -> PriceSnapshot:
        ref = self._db.collection(_WATCHES).document(watch_id)
        if not ref.get().exists:
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
        ref.collection(_SNAPSHOTS).document(snap.id).set(
            {
                "price": snap.price,
                "currency": snap.currency,
                "cabin": snap.cabin,
                "fare_basis": snap.fare_basis,
                "carrier": snap.carrier,
                "provider": snap.provider,
                "observed_at": snap.observed_at,
            }
        )
        return snap

    def list_snapshots(self, watch_id: str, limit: int = 100) -> list[PriceSnapshot]:
        ref = self._db.collection(_WATCHES).document(watch_id)
        if not ref.get().exists:
            raise WatchNotFoundError(watch_id)
        docs = (
            ref.collection(_SNAPSHOTS)
            .order_by("observed_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [self._to_snapshot(d, watch_id) for d in docs]
