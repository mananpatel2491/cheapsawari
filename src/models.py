"""Normalized domain models shared across providers and the API layer.

The whole point of `Offer` is to decouple the rest of the app from any single fare
provider's response shape. Every FareProvider must return this exact structure, so
downstream slices (persistence, signal detection, alerts) never depend on Amadeus.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

# --- Slice 7: round-trip + date flexibility -------------------------------
#: Trip shapes a watch can track. Multi-city is a planned later slice.
TRIP_TYPES = ("one_way", "round_trip")
#: Cap on how many days a flexible leg may span past its anchor date. Bounds the
#: per-poll provider fan-out (a flexible round trip queries
#: (depart_flex_days+1) + (return_flex_days+1) dates), keeping quota predictable.
MAX_FLEX_DAYS = 21


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
    """Input for registering a new watch (a trip the user wants tracked).

    Supports one-way and round-trip shapes with per-leg date flexibility (Slice 7).
    For a flexible leg, the anchor date is the *earliest* date and the leg is searched
    forward across ``flex_days`` days; the watch tracks the cheapest date in that window.
    """

    origin: str = Field(..., description="Origin IATA code.")
    destination: str = Field(..., description="Destination IATA code.")
    departure_date: _date = Field(..., description="Outbound date (earliest, if flexible).")
    cabin: str = Field("ECONOMY", description="Cabin class to track.")
    trip_type: str = Field("one_way", description="'one_way' or 'round_trip'.")
    return_date: _date | None = Field(
        None, description="Return date (earliest, if flexible). Required for round_trip."
    )
    depart_flex_days: int = Field(
        0, ge=0, le=MAX_FLEX_DAYS, description="Search the outbound up to N days past departure_date."
    )
    return_flex_days: int = Field(
        0, ge=0, le=MAX_FLEX_DAYS, description="Search the return up to N days past return_date."
    )

    @model_validator(mode="after")
    def _check_trip(self) -> "WatchCreate":
        if self.trip_type not in TRIP_TYPES:
            raise ValueError(f"trip_type must be one of {TRIP_TYPES}.")
        if self.trip_type == "round_trip":
            if self.return_date is None:
                raise ValueError("return_date is required for a round_trip.")
            if self.return_date < self.departure_date:
                raise ValueError("return_date must not be before departure_date.")
        else:
            # Normalize a one-way watch so return fields can't carry stray data.
            self.return_date = None
            self.return_flex_days = 0
        return self


class Watch(WatchCreate):
    """A persisted watch. Identity + lifecycle on top of the user's input."""

    id: str = Field(..., description="Stable watch id (uuid4).")
    active: bool = Field(True, description="Whether the scheduler (Slice 3) should poll it.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")


class PriceSnapshot(BaseModel):
    """One observed fare for a watch — a row in the price time-series.

    ``price`` is the *trip total*: the single fare for a one-way watch, or
    outbound+return for a round trip. Signal detection (Slice 4) reads ``price``, so
    it works unchanged on round trips. ``currency``/``cabin``/``fare_basis``/``carrier``
    describe the outbound leg. The ``outbound_*``/``return_*`` fields (Slice 7) break the
    total down and record which flexible date in each window was cheapest.
    """

    id: str = Field(..., description="Stable snapshot id (uuid4).")
    watch_id: str = Field(..., description="The watch this observation belongs to.")
    price: float = Field(..., ge=0, description="Trip total (outbound + return for round trips).")
    currency: str
    cabin: str
    fare_basis: str | None = None
    carrier: str | None = None
    provider: str
    observed_at: datetime
    # Slice 7 — per-leg breakdown (None on legacy one-way snapshots).
    outbound_price: float | None = Field(None, description="Cheapest outbound fare.")
    outbound_date: _date | None = Field(None, description="Cheapest outbound date in the window.")
    return_price: float | None = Field(None, description="Cheapest return fare (round trips).")
    return_date: _date | None = Field(None, description="Cheapest return date in the window.")


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


# --- Slice 6: auth + admin -------------------------------------------------

class AddUserRequest(BaseModel):
    """Admin input for granting a Gmail address access to the app."""

    email: str = Field(..., description="The Google account email to allow (stored lower-cased).")


class AllowedUser(BaseModel):
    """A persisted allowlist entry — one Google account permitted to use the app."""

    email: str = Field(..., description="Google account email (lower-cased), the primary key.")
    added_by: str = Field(..., description="Email of the admin who granted access.")
    added_at: datetime = Field(..., description="UTC timestamp access was granted.")


class SessionUser(BaseModel):
    """The authenticated caller resolved from the signed session cookie."""

    email: str = Field(..., description="Signed-in Google account email.")
    is_admin: bool = Field(..., description="True when email == the configured ADMIN_EMAIL.")
