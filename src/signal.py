"""Signal detection — Slice 4.

Reads a watch's price-snapshot time-series and decides whether a *bucket
reopened*: the latest observed fare has dropped meaningfully below its recent
trailing average. This is the insight the whole tracker exists to surface —
yield-managed inventory occasionally releases a cheaper booking class, and we
want to catch that exact moment.

Pure and provider-agnostic: snapshots in, a :class:`Signal` (or ``None``) out.
No I/O, no store, no provider — so it's trivially testable and is reused by both
the on-demand endpoint and the scheduled poll.

Why a *rising-edge* trigger instead of a simple level check: an unattended daily
poll would otherwise re-fire every single day the price stayed low. We alert only
on the transition from "not dropped" to "dropped" — the moment the bucket
reopens — which yields exactly one alert per reopening event while persisting no
alert state at all (the snapshot series itself is the memory).
"""
from __future__ import annotations

from datetime import timedelta
from statistics import mean

from pydantic import BaseModel, Field

from .models import PriceSnapshot

#: Minimum snapshots needed to evaluate a rising edge: the current point, a prior
#: to form its baseline, and a prior-of-prior so the preceding point also has a
#: baseline to be judged against.
_MIN_HISTORY = 3


class Signal(BaseModel):
    """A detected fare event for a watch (currently only ``bucket_reopened``)."""

    watch_id: str
    kind: str = Field("bucket_reopened", description="Signal type.")
    current_price: float = Field(..., description="Latest observed price that triggered it.")
    baseline_price: float = Field(..., description="Trailing moving-average it dropped below.")
    drop_pct: float = Field(..., description="How far below baseline, as a percentage.")
    currency: str
    fare_basis: str | None = Field(None, description="The reopened bucket, if known.")
    observed_at: object = Field(..., description="When the triggering fare was observed (UTC).")
    window_days: int = Field(..., description="Trailing window used for the baseline.")
    threshold_pct: float = Field(..., description="Drop threshold that was crossed.")
    # Slice 16 — route of the triggering snapshot (from its legs), so an alert/email
    # reads as a place, not a UUID. Optional: legacy snapshots may carry no legs.
    origin: str | None = Field(None, description="Trip origin (first leg).")
    destination: str | None = Field(None, description="Trip destination (last leg).")


class SignalResult(BaseModel):
    """On-demand detection result — a stable shape for the API/Bruno to assert on."""

    watch_id: str
    detected: bool
    signal: Signal | None = None


def _evaluate(
    points: list[PriceSnapshot], idx: int, threshold_pct: float, window_days: int
) -> tuple[bool, float | None]:
    """Is ``points[idx]`` a drop vs the mean of the points before it, within window?

    Returns ``(is_drop, baseline)``. ``baseline`` is ``None`` when there is no
    prior observation inside the trailing window (so no judgement is possible).
    """
    pivot = points[idx]
    window_start = pivot.observed_at - timedelta(days=window_days)
    priors = [p.price for p in points[:idx] if p.observed_at >= window_start]
    if not priors:
        return False, None
    baseline = mean(priors)
    is_drop = pivot.price < baseline * (1 - threshold_pct / 100)
    return is_drop, baseline


def detect_reopening(
    snapshots: list[PriceSnapshot],
    threshold_pct: float = 15.0,
    window_days: int = 7,
) -> Signal | None:
    """Detect a freshly reopened cheaper bucket in a watch's price history.

    Fires when the most recent snapshot sits more than ``threshold_pct`` below the
    mean of the snapshots in the preceding ``window_days``, *and* the snapshot
    just before it did not already qualify — i.e. only on the rising edge.

    Args:
        snapshots: A watch's snapshots, in any order (newest-first is fine).
        threshold_pct: Percent below the trailing average that counts as a drop.
        window_days: Length of the trailing moving-average window, in days.

    Returns:
        A :class:`Signal` on a fresh reopening, else ``None``.
    """
    if len(snapshots) < _MIN_HISTORY:
        return None

    points = sorted(snapshots, key=lambda s: s.observed_at)
    last = len(points) - 1

    drop_now, baseline = _evaluate(points, last, threshold_pct, window_days)
    if not drop_now or baseline is None:
        return None

    # Rising edge: if the previous point was already a drop, this low is a
    # continuation, not a reopening — we've alerted on it before.
    drop_prior, _ = _evaluate(points, last - 1, threshold_pct, window_days)
    if drop_prior:
        return None

    current = points[last]
    drop_pct = round((baseline - current.price) / baseline * 100, 2)
    origin = destination = None
    if current.legs:
        origin = current.legs[0].origin
        destination = current.legs[-1].destination
    return Signal(
        watch_id=current.watch_id,
        current_price=current.price,
        baseline_price=round(baseline, 2),
        drop_pct=drop_pct,
        currency=current.currency,
        fare_basis=current.fare_basis,
        observed_at=current.observed_at,
        window_days=window_days,
        threshold_pct=threshold_pct,
        origin=origin,
        destination=destination,
    )
