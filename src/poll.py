"""Quota-capped poll engine — Slice 3.

Iterates the active watches, queries the configured FareProvider for each, and
records a price snapshot. This is the unattended heartbeat of the tracker; in
production a once-a-day Cloud Scheduler job calls the endpoint that wraps it.

The cap is the whole point: external fare APIs are quota-limited (Amadeus free
tier ≈ 2,000 req/month), so a single run never queries more than
`max_per_run` watches. One provider failure does not abort the run — it's
counted and the run continues.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .providers import FareProvider, ProviderError
from .store import WatchRepository


class PollSummary(BaseModel):
    """Outcome of one poll run — what the scheduler/endpoint returns."""

    active_watches: int = Field(..., description="Active watches found.")
    polled: int = Field(..., description="Watches actually queried this run.")
    recorded: int = Field(..., description="Snapshots stored (provider returned an offer).")
    no_inventory: int = Field(..., description="Watches the provider had no offer for.")
    errors: int = Field(..., description="Watches that hit a provider error (run continued).")
    skipped_over_cap: int = Field(
        ..., description="Active watches not polled because the per-run cap was reached."
    )


def poll_active_watches(
    repo: WatchRepository, provider: FareProvider, max_per_run: int
) -> PollSummary:
    """Poll up to ``max_per_run`` active watches and record snapshots.

    Args:
        repo: Where watches live and snapshots are written.
        provider: The fare data source to query.
        max_per_run: Hard cap on queries this run (quota protection).

    Returns:
        A :class:`PollSummary` tallying the run. Never raises for a single
        watch's provider error — those are counted in ``errors``.
    """
    active = repo.list_watches(active_only=True)
    polled = recorded = no_inventory = errors = 0

    for watch in active[:max_per_run]:
        polled += 1
        try:
            offer = provider.get_cheapest_offer(
                watch.origin, watch.destination, watch.departure_date, watch.cabin
            )
        except ProviderError:
            errors += 1
            continue

        if offer is None:
            no_inventory += 1
        else:
            repo.add_snapshot(watch.id, offer)
            recorded += 1

    return PollSummary(
        active_watches=len(active),
        polled=polled,
        recorded=recorded,
        no_inventory=no_inventory,
        errors=errors,
        skipped_over_cap=max(0, len(active) - max_per_run),
    )
