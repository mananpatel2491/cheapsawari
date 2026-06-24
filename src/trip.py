"""Trip pricing — Slice 7 (flexible round-trip) + Slice 9 (multi-city).

Turns a :class:`Watch` of any shape — one-way, round-trip, or multi-city — into a
single cheapest :class:`TripQuote`, using only the existing per-date
``FareProvider.get_cheapest_offer`` seam:

    * every watch resolves to an ordered list of legs (``Watch.resolved_legs``):
      one-way = 1 leg, round-trip = 2, multi-city = N.
    * a leg with ``flex_days = N`` is searched across N+1 consecutive dates from its
      anchor, keeping the cheapest.
    * the trip total is the sum of the legs.

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
    """The cheapest priced trip for a watch at one point in time (one Offer per leg)."""

    legs: list[Offer]
    total: float

    @property
    def currency(self) -> str:
        return self.legs[0].currency


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

    *Every* leg must have inventory somewhere in its window; if any leg is empty there
    is no complete trip to quote and None is returned.
    """
    priced: list[Offer] = []
    for leg in watch.resolved_legs:
        offer = _cheapest_in_window(
            provider, leg.origin, leg.destination, leg.date, leg.flex_days, watch.cabin
        )
        if offer is None:
            return None
        priced.append(offer)

    total = round(sum(o.price for o in priced), 2)
    return TripQuote(legs=priced, total=total)
