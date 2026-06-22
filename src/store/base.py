"""The WatchRepository contract — the persistence seam."""
from __future__ import annotations

import abc

from ..models import Offer, PriceSnapshot, Watch, WatchCreate


class WatchNotFoundError(LookupError):
    """Raised when an operation targets a watch id that does not exist."""


class WatchRepository(abc.ABC):
    """Abstract store for watches and their price-snapshot time-series.

    Implementations must be safe to call per-request. They translate between the
    domain models and whatever backing store they use, leaking nothing upward.
    """

    @abc.abstractmethod
    def create_watch(self, data: WatchCreate) -> Watch:
        """Persist a new watch and return it (with id + created_at assigned)."""

    @abc.abstractmethod
    def get_watch(self, watch_id: str) -> Watch | None:
        """Return the watch, or None if it does not exist."""

    @abc.abstractmethod
    def list_watches(self, active_only: bool = False) -> list[Watch]:
        """Return all watches, newest first. If active_only, skip paused watches."""

    @abc.abstractmethod
    def delete_watch(self, watch_id: str) -> bool:
        """Delete a watch (and cascade its snapshots). True if it existed."""

    @abc.abstractmethod
    def add_snapshot(self, watch_id: str, offer: Offer) -> PriceSnapshot:
        """Record an observed offer as a snapshot for the watch.

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """

    @abc.abstractmethod
    def list_snapshots(self, watch_id: str, limit: int = 100) -> list[PriceSnapshot]:
        """Return snapshots for a watch, newest first.

        Raises:
            WatchNotFoundError: If the watch does not exist.
        """
