"""The WatchRepository contract — the persistence seam."""
from __future__ import annotations

import abc
import uuid

from ..models import Offer, PriceSnapshot, SnapshotLeg, Watch, WatchCreate


class WatchNotFoundError(LookupError):
    """Raised when an operation targets a watch id that does not exist."""


def build_snapshot(
    watch_id: str,
    legs: list[Offer],
    *,
    total: float | None = None,
    trip_type: str = "one_way",
) -> PriceSnapshot:
    """Assemble a :class:`PriceSnapshot` from the priced legs of a trip.

    Shared by every store so the leg → snapshot mapping lives in one place. ``price`` is
    the trip total (defaults to the sum of the legs); ``legs`` is the canonical per-leg
    breakdown. The first leg supplies the descriptive fields; ``outbound_*``/``return_*``
    are kept as convenience fields for the one-way/round-trip cases.
    """
    head = legs[0]
    snap_legs = [
        SnapshotLeg(
            origin=o.origin, destination=o.destination, date=o.departure_date,
            price=o.price, fare_basis=o.fare_basis, carrier=o.carrier,
        )
        for o in legs
    ]
    return_price = return_date = None
    if trip_type == "round_trip" and len(legs) >= 2:
        return_price = legs[-1].price
        return_date = legs[-1].departure_date
    return PriceSnapshot(
        id=str(uuid.uuid4()),
        watch_id=watch_id,
        price=total if total is not None else round(sum(o.price for o in legs), 2),
        currency=head.currency,
        cabin=head.cabin,
        fare_basis=head.fare_basis,
        carrier=head.carrier,
        provider=head.provider,
        observed_at=head.observed_at,
        legs=snap_legs,
        outbound_price=head.price,
        outbound_date=head.departure_date,
        return_price=return_price,
        return_date=return_date,
    )


class WatchRepository(abc.ABC):
    """Abstract store for watches and their price-snapshot time-series.

    Implementations must be safe to call per-request. They translate between the
    domain models and whatever backing store they use, leaking nothing upward.
    """

    @abc.abstractmethod
    def create_watch(self, data: WatchCreate, owner_email: str | None = None) -> Watch:
        """Persist a new watch (owned by ``owner_email``) and return it."""

    @abc.abstractmethod
    def get_watch(self, watch_id: str) -> Watch | None:
        """Return the watch, or None if it does not exist. (Ownership is enforced by the API.)"""

    @abc.abstractmethod
    def update_watch(self, watch_id: str, data: WatchCreate) -> Watch:
        """Replace a watch's trip definition in place and return the updated watch.

        Overwrites the trip fields (origin/destination/dates/flex/cabin/trip_type/legs)
        from ``data`` while preserving the watch's identity and lifecycle — ``id``,
        ``created_at``, ``owner_email`` and ``active`` are untouched. Price snapshots are
        kept (the watch keeps its history); a caller wanting a clean series should delete
        and re-create. (Ownership is enforced by the API.)

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """

    @abc.abstractmethod
    def list_watches(self, active_only: bool = False, owner_email: str | None = None) -> list[Watch]:
        """Return watches, newest first.

        If ``active_only``, skip paused watches. If ``owner_email`` is given, return only
        that user's watches; ``None`` returns every owner's (used by the scheduler poll and
        the admin's see-all view).
        """

    @abc.abstractmethod
    def delete_watch(self, watch_id: str) -> bool:
        """Delete a watch (and cascade its snapshots). True if it existed."""

    @abc.abstractmethod
    def add_snapshot(
        self,
        watch_id: str,
        legs: list[Offer],
        *,
        total: float | None = None,
        trip_type: str = "one_way",
    ) -> PriceSnapshot:
        """Record an observed trip as a snapshot for the watch.

        ``legs`` is the priced legs (one Offer each); the first supplies the snapshot's
        descriptive fields. ``total`` defaults to the sum of the legs. ``trip_type`` lets
        the round-trip convenience fields be populated. See :func:`build_snapshot`.

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """

    @abc.abstractmethod
    def list_snapshots(self, watch_id: str, limit: int = 100) -> list[PriceSnapshot]:
        """Return snapshots for a watch, newest first.

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """
