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
