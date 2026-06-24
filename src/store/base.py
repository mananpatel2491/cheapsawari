"""The WatchRepository contract — the persistence seam."""
from __future__ import annotations

import abc
import uuid
from datetime import date as _date

from ..models import Offer, PriceSnapshot, Watch, WatchCreate


class WatchNotFoundError(LookupError):
    """Raised when an operation targets a watch id that does not exist."""


def build_snapshot(
    watch_id: str,
    offer: Offer,
    *,
    total: float | None = None,
    outbound_date: _date | None = None,
    return_offer: Offer | None = None,
) -> PriceSnapshot:
    """Assemble a :class:`PriceSnapshot` from an outbound offer (+ optional return).

    Shared by every store so the one-way ↔ round-trip mapping lives in one place.
    ``price`` is the trip total; the outbound offer supplies the descriptive fields.
    """
    return PriceSnapshot(
        id=str(uuid.uuid4()),
        watch_id=watch_id,
        price=total if total is not None else offer.price,
        currency=offer.currency,
        cabin=offer.cabin,
        fare_basis=offer.fare_basis,
        carrier=offer.carrier,
        provider=offer.provider,
        observed_at=offer.observed_at,
        outbound_price=offer.price,
        outbound_date=outbound_date or offer.departure_date,
        return_price=return_offer.price if return_offer else None,
        return_date=return_offer.departure_date if return_offer else None,
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
        offer: Offer,
        *,
        total: float | None = None,
        outbound_date=None,
        return_offer: Offer | None = None,
    ) -> PriceSnapshot:
        """Record an observed trip as a snapshot for the watch.

        ``offer`` is the outbound leg (its fields describe the snapshot's
        currency/cabin/fare_basis/carrier/provider/observed_at). For a round trip pass
        ``return_offer`` and the ``total`` (outbound+return); both default to a one-way
        snapshot (total = outbound price). ``outbound_date`` records which flexible date
        was cheapest (defaults to the offer's departure_date).

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """

    @abc.abstractmethod
    def list_snapshots(self, watch_id: str, limit: int = 100) -> list[PriceSnapshot]:
        """Return snapshots for a watch, newest first.

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """
