"""Deterministic in-memory fare provider.

Default provider for tests and local dev: it hits no network and burns no API quota,
yet returns stable, plausible offers so Bruno assertions are reproducible. The price is
a pure function of (origin, destination, date, cabin), so the same query always yields
the same number — exactly what contract tests need.
"""
from __future__ import annotations

import hashlib
from datetime import date as _date

from ..models import Offer
from .base import FareProvider

# A small ring of fare-basis codes ("buckets") to make output look real and to give
# later signal-detection slices something bucket-shaped to react to.
_BUCKETS = ["QLXOW", "HLXOW", "MLXOW", "KLXOW", "VLXOW"]
_CABIN_MULTIPLIER = {"ECONOMY": 1.0, "PREMIUM_ECONOMY": 1.6, "BUSINESS": 3.2, "FIRST": 5.0}


def _stable_int(*parts: str) -> int:
    """Deterministic non-negative int from the given parts (stable across runs/machines)."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class MockFareProvider(FareProvider):
    name = "mock"

    #: Reserved IATA-shaped code that simulates "no inventory" so the 404 path is testable.
    NO_INVENTORY_SENTINEL = "ZZZ"

    def get_cheapest_offer(
        self, origin: str, destination: str, departure_date: _date, cabin: str = "ECONOMY"
    ) -> Offer | None:
        # Sentinel route lets contract tests exercise the "no offers" (404) branch.
        if self.NO_INVENTORY_SENTINEL in (origin.upper(), destination.upper()):
            return None

        seed = _stable_int(origin, destination, departure_date.isoformat(), cabin)

        # Base economy fare in the $120–$719 range, scaled by cabin.
        base = 120 + (seed % 600)
        multiplier = _CABIN_MULTIPLIER.get(cabin.upper(), 1.0)
        price = round(base * multiplier, 2)

        bucket = _BUCKETS[seed % len(_BUCKETS)]
        # Deterministic two-letter pseudo-carrier so output looks like an airline code.
        carrier = chr(65 + seed % 26) + chr(65 + (seed // 26) % 26)

        return Offer(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            price=price,
            currency="USD",
            cabin=cabin.upper(),
            fare_basis=bucket,
            carrier=carrier,
            provider=self.name,
        )
