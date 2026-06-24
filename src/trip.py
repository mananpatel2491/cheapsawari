"""Trip pricing — Slice 7 (round-trip + date flexibility).

Turns a :class:`Watch` (which may be one-way or round-trip, with a flexible date
window on each leg) into a single cheapest :class:`TripQuote`, using only the
existing per-date ``FareProvider.get_cheapest_offer`` seam:

    * a leg with ``flex_days = N`` is searched across N+1 consecutive dates from its
      anchor, keeping the cheapest;
    * a round trip prices both legs and sums them.

Provider-agnostic by construction — it composes single-date lookups, so it works
identically on the mock (deterministic tests) and on Travelpayouts (cached fares).
A ``ProviderError`` from any underlying lookup propagates unchanged, so the caller's
existing error handling (refresh → 502, poll → counted) is preserved.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import timedelta

from pydantic import BaseModel

from .models import Offer, Watch
from .providers import FareProvider


class TripQuote(BaseModel):
    """The cheapest priced trip for a watch at one point in time."""

    outbound: Offer
    return_leg: Offer | None = None
    total: float

    @property
    def currency(self) -> str:
        return self.outbound.currency


def _cheapest_in_window(
    provider: FareProvider,
    origin: str,
    destination: str,
    anchor: _date,
    flex_days: int,
    cabin: str,
) -> Offer | None:
    """Cheapest offer for origin→destination across [anchor, anchor+flex_days].

    Returns None only if *every* date in the window has no inventory. Each date is a
    separate provider lookup; a ProviderError propagates (we don't mask a real failure
    as "no inventory").
    """
    best: Offer | None = None
    for offset in range(flex_days + 1):
        offer = provider.get_cheapest_offer(
            origin, destination, anchor + timedelta(days=offset), cabin
        )
        if offer is not None and (best is None or offer.price < best.price):
            best = offer
    return best


def price_watch_trip(provider: FareProvider, watch: Watch) -> TripQuote | None:
    """Price a watch's cheapest trip, or None if it has no bookable inventory.

    For a round trip, *both* legs must have inventory somewhere in their windows;
    otherwise there is no complete trip to quote and None is returned.
    """
    outbound = _cheapest_in_window(
        provider, watch.origin, watch.destination,
        watch.departure_date, watch.depart_flex_days, watch.cabin,
    )
    if outbound is None:
        return None

    return_leg: Offer | None = None
    if watch.trip_type == "round_trip" and watch.return_date is not None:
        return_leg = _cheapest_in_window(
            provider, watch.destination, watch.origin,
            watch.return_date, watch.return_flex_days, watch.cabin,
        )
        if return_leg is None:
            return None

    total = round(outbound.price + (return_leg.price if return_leg else 0.0), 2)
    return TripQuote(outbound=outbound, return_leg=return_leg, total=total)
