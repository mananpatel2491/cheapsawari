"""Quota-capped poll engine — Slice 3.

Iterates the active watches, queries the configured FareProvider for each, and
records a price snapshot. This is the unattended heartbeat of the tracker; in
production a once-a-day Cloud Scheduler job calls the endpoint that wraps it.

The cap is the whole point: external fare APIs are quota-limited (Amadeus
Self-Service free quotas are per-API and vary — confirm yours in the account
Workspace), so a single run never queries more than `max_per_run` watches. One
provider failure does not abort the run — it's counted and the run continues.
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from . import obs
from .alerts import AlertChannel, AlertError
from .providers import FareProvider, ProviderError
from .signal import detect_reopening
from .store import WatchRepository
from .trip import price_watch_trip

_log = obs.get_logger("poll")


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
    alerts_fired: int = Field(
        0, description="Reopened-bucket alerts delivered this run (Slice 4)."
    )


def poll_active_watches(
    repo: WatchRepository,
    provider: FareProvider,
    max_per_run: int,
    *,
    alerter: AlertChannel | None = None,
    threshold_pct: float = 15.0,
    window_days: int = 7,
) -> PollSummary:
    """Poll up to ``max_per_run`` active watches, record snapshots, and alert.

    After a watch records a fresh snapshot, its price series is re-examined for a
    just-reopened cheaper bucket (Slice 4). On a rising-edge drop the optional
    ``alerter`` delivers exactly one alert. Detection/alert failures are isolated
    per watch — they never abort the run.

    Args:
        repo: Where watches live and snapshots are written.
        provider: The fare data source to query.
        max_per_run: Hard cap on queries this run (quota protection).
        alerter: Channel to deliver reopened-bucket alerts; ``None`` disables alerting.
        threshold_pct: Drop below the trailing average that counts as a reopening.
        window_days: Trailing moving-average window for the baseline.

    Returns:
        A :class:`PollSummary` tallying the run. Never raises for a single
        watch's provider error — those are counted in ``errors``.
    """
    active = repo.list_watches(active_only=True)
    polled = recorded = no_inventory = errors = alerts_fired = 0

    for watch in active[:max_per_run]:
        polled += 1
        try:
            quote = price_watch_trip(provider, watch)
        except ProviderError as exc:
            errors += 1
            obs.event(_log, "provider.error", level=logging.WARNING, op="poll",
                      watch_id=watch.id, provider=provider.name, detail=str(exc))
            continue

        if quote is None:
            no_inventory += 1
            continue

        repo.add_snapshot(
            watch.id, quote.legs, total=quote.total, trip_type=watch.trip_type
        )
        recorded += 1

        if alerter is None:
            continue
        # Detect on the freshly extended series; one watch's hiccup must not
        # sink the whole scheduled run.
        try:
            signal = detect_reopening(
                repo.list_snapshots(watch.id), threshold_pct, window_days
            )
            if signal is not None:
                alerter.send(signal)
                alerts_fired += 1
                obs.event(_log, "alert.fired", watch_id=watch.id,
                          drop_pct=signal.drop_pct, price=signal.current_price)
        except AlertError as exc:
            obs.event(_log, "alert.error", level=logging.WARNING,
                      watch_id=watch.id, detail=str(exc))
        except Exception:  # detection/store hiccup — log and keep polling
            obs.event(_log, "poll.watch_error", level=logging.ERROR,
                      watch_id=watch.id, exc_info=True)

    summary = PollSummary(
        active_watches=len(active),
        polled=polled,
        recorded=recorded,
        no_inventory=no_inventory,
        errors=errors,
        skipped_over_cap=max(0, len(active) - max_per_run),
        alerts_fired=alerts_fired,
    )
    # One line per run = the daily heartbeat. Search: jsonPayload.event="poll.run".
    obs.event(_log, "poll.run", **summary.model_dump())
    return summary
