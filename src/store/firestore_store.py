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
from .base import WatchNotFoundError, WatchRepository, build_snapshot

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
        rd = d.get("return_date")
        return Watch(
            id=doc.id,
            origin=d["origin"],
            destination=d["destination"],
            departure_date=_date.fromisoformat(d["departure_date"]),
            cabin=d["cabin"],
            active=bool(d.get("active", True)),
            created_at=_as_utc(d["created_at"]),
            trip_type=d.get("trip_type", "one_way"),
            return_date=_date.fromisoformat(rd) if rd else None,
            depart_flex_days=int(d.get("depart_flex_days", 0)),
            return_flex_days=int(d.get("return_flex_days", 0)),
            owner_email=d.get("owner_email"),
        )

    @staticmethod
    def _to_snapshot(doc, watch_id: str) -> PriceSnapshot:
        d = doc.to_dict()
        od, rd = d.get("outbound_date"), d.get("return_date")
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
            outbound_price=d.get("outbound_price"),
            outbound_date=_date.fromisoformat(od) if od else None,
            return_price=d.get("return_price"),
            return_date=_date.fromisoformat(rd) if rd else None,
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
        )
        self._db.collection(_WATCHES).document(watch.id).set(
            {
                "origin": watch.origin,
                "destination": watch.destination,
                "departure_date": watch.departure_date.isoformat(),
                "cabin": watch.cabin,
                "active": watch.active,
                "created_at": watch.created_at,
                "trip_type": watch.trip_type,
                "return_date": watch.return_date.isoformat() if watch.return_date else None,
                "depart_flex_days": watch.depart_flex_days,
                "return_flex_days": watch.return_flex_days,
                "owner_email": watch.owner_email,
            }
        )
        return watch

    def get_watch(self, watch_id: str) -> Watch | None:
        doc = self._db.collection(_WATCHES).document(watch_id).get()
        return self._to_watch(doc) if doc.exists else None

    def list_watches(self, active_only: bool = False, owner_email: str | None = None) -> list[Watch]:
        # Filter in Python (personal scale = few watches) to avoid composite indexes.
        watches = [self._to_watch(d) for d in self._db.collection(_WATCHES).stream()]
        if active_only:
            watches = [w for w in watches if w.active]
        if owner_email is not None:
            watches = [w for w in watches if w.owner_email == owner_email]
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
    def add_snapshot(
        self,
        watch_id: str,
        offer: Offer,
        *,
        total: float | None = None,
        outbound_date=None,
        return_offer: Offer | None = None,
    ) -> PriceSnapshot:
        ref = self._db.collection(_WATCHES).document(watch_id)
        if not ref.get().exists:
            raise WatchNotFoundError(watch_id)
        snap = build_snapshot(
            watch_id, offer, total=total, outbound_date=outbound_date, return_offer=return_offer
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
                "outbound_price": snap.outbound_price,
                "outbound_date": snap.outbound_date.isoformat() if snap.outbound_date else None,
                "return_price": snap.return_price,
                "return_date": snap.return_date.isoformat() if snap.return_date else None,
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
