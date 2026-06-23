"""Normalized domain models shared across providers and the API layer.

The whole point of `Offer` is to decouple the rest of the app from any single fare
provider's response shape. Every FareProvider must return this exact structure, so
downstream slices (persistence, signal detection, alerts) never depend on Amadeus.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Offer(BaseModel):
    """The cheapest fare observed for a route on a given departure date.

    This is the canonical record a future slice will snapshot into the price
    time-series. Keep it provider-agnostic.
    """

    origin: str = Field(..., description="Origin IATA code, e.g. 'JFK'.")
    destination: str = Field(..., description="Destination IATA code, e.g. 'LAX'.")
    departure_date: _date = Field(..., description="Departure date (local to origin).")

    price: float = Field(..., ge=0, description="Total price for the offer.")
    currency: str = Field(..., description="ISO 4217 currency code, e.g. 'USD'.")
    cabin: str = Field(..., description="Cabin class, e.g. 'ECONOMY'.")
    fare_basis: str | None = Field(
        None,
        description="Fare basis / booking class code — the 'bucket' (e.g. 'QLXOW'). "
        "Central to the product thesis; may be absent for some providers.",
    )
    carrier: str | None = Field(None, description="Validating/marketing carrier IATA code.")

    provider: str = Field(..., description="Which FareProvider produced this offer.")
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp the offer was observed — the time-series key.",
    )


# --- Slice 2: watches + persistence ---------------------------------------

class WatchCreate(BaseModel):
    """Input for registering a new watch (a route+date the user wants tracked)."""

    origin: str = Field(..., description="Origin IATA code.")
    destination: str = Field(..., description="Destination IATA code.")
    departure_date: _date = Field(..., description="Departure date to track.")
    cabin: str = Field("ECONOMY", description="Cabin class to track.")


class Watch(WatchCreate):
    """A persisted watch. Identity + lifecycle on top of the user's input."""

    id: str = Field(..., description="Stable watch id (uuid4).")
    active: bool = Field(True, description="Whether the scheduler (Slice 3) should poll it.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")


class PriceSnapshot(BaseModel):
    """One observed fare for a watch — a row in the price time-series.

    Built from an :class:`Offer` and tied to a watch. This is what signal
    detection (Slice 4) will read to spot drops / reopened buckets.
    """

    id: str = Field(..., description="Stable snapshot id (uuid4).")
    watch_id: str = Field(..., description="The watch this observation belongs to.")
    price: float = Field(..., ge=0)
    currency: str
    cabin: str
    fare_basis: str | None = None
    carrier: str | None = None
    provider: str
    observed_at: datetime


class RefreshResult(BaseModel):
    """Outcome of polling a watch once and (maybe) recording a snapshot."""

    recorded: bool = Field(..., description="True if a snapshot was stored.")
    reason: str | None = Field(None, description="Why nothing was recorded (e.g. no inventory).")
    snapshot: PriceSnapshot | None = None


# --- Slice 4: signal detection + alerts -----------------------------------

class SnapshotCreate(BaseModel):
    """Input for manually recording an observed fare for a watch.

    Lets a user log a price they spotted (or backfill history) without waiting for
    the scheduled poll. Stored exactly like a polled snapshot, tagged
    ``provider='manual'``. Also the deterministic way contract tests seed a price
    series — the mock provider is stateless, so polling alone can't build a trend.
    """

    price: float = Field(..., ge=0, description="Observed total price.")
    currency: str = Field("USD", description="ISO 4217 currency code.")
    cabin: str | None = Field(None, description="Cabin class; defaults to the watch's cabin.")
    fare_basis: str | None = Field(None, description="Observed fare basis / bucket code.")
    carrier: str | None = Field(None, description="Validating/marketing carrier IATA code.")
    observed_at: datetime | None = Field(
        None, description="When it was observed (UTC). Defaults to now; set it for backfill."
    )
