"""Normalized domain models shared across providers and the API layer.

The whole point of `Offer` is to decouple the rest of the app from any single fare
provider's response shape. Every FareProvider must return this exact structure, so
downstream slices (persistence, signal detection, alerts) never depend on Amadeus.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

# --- Slice 7/9: flexible round-trip + multi-city --------------------------
#: Trip shapes a watch can track. ``multi_city`` (Slice 9) is an explicit chain of
#: legs — also how a user models a chosen transfer hub or first port-of-entry.
TRIP_TYPES = ("one_way", "round_trip", "multi_city")
#: Cap on how many days a flexible leg may span past its anchor date. Bounds the
#: per-poll provider fan-out (each leg queries flex_days+1 dates), keeping quota
#: predictable.
MAX_FLEX_DAYS = 21
#: Cap on legs in a multi-city trip (quota + UI sanity).
MAX_LEGS = 6


class TripLeg(BaseModel):
    """One leg of a trip: a route + an (earliest) date with optional flexibility.

    The unit a multi-city trip is built from; one-way and round-trip watches resolve
    to a list of these too (see ``WatchCreate.resolved_legs``).
    """

    origin: str = Field(..., description="Leg origin IATA code.")
    destination: str = Field(..., description="Leg destination IATA code.")
    date: _date = Field(..., description="Leg date (earliest, if flexible).")
    flex_days: int = Field(0, ge=0, le=MAX_FLEX_DAYS, description="Search up to N days past date.")

    @model_validator(mode="after")
    def _normalize(self) -> "TripLeg":
        self.origin = self.origin.upper()
        self.destination = self.destination.upper()
        if self.origin == self.destination:
            raise ValueError("a leg's origin and destination must differ.")
        return self


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

    Three shapes, all with per-leg date flexibility (anchor date = earliest; the leg is
    searched forward across ``flex_days`` days, tracking the cheapest date):

    * ``one_way``    — origin → destination on departure_date.
    * ``round_trip`` — adds the return (destination → origin) on return_date.
    * ``multi_city`` — an explicit ``legs`` chain (Slice 9); origin/destination/
      departure_date are derived from the first/last leg, so a client may omit them.
    """

    origin: str | None = Field(None, description="Origin IATA code (derived for multi_city).")
    destination: str | None = Field(None, description="Destination IATA code (derived for multi_city).")
    departure_date: _date | None = Field(None, description="Outbound date (derived for multi_city).")
    cabin: str = Field("ECONOMY", description="Cabin class to track.")
    trip_type: str = Field("one_way", description="'one_way' | 'round_trip' | 'multi_city'.")
    return_date: _date | None = Field(
        None, description="Return date (earliest, if flexible). Required for round_trip."
    )
    depart_flex_days: int = Field(
        0, ge=0, le=MAX_FLEX_DAYS, description="Search the outbound up to N days past departure_date."
    )
    return_flex_days: int = Field(
        0, ge=0, le=MAX_FLEX_DAYS, description="Search the return up to N days past return_date."
    )
    legs: list[TripLeg] | None = Field(
        None, description="Ordered legs for multi_city (2..MAX_LEGS). Ignored otherwise."
    )

    @model_validator(mode="after")
    def _check_trip(self) -> "WatchCreate":
        if self.trip_type not in TRIP_TYPES:
            raise ValueError(f"trip_type must be one of {TRIP_TYPES}.")

        if self.trip_type == "multi_city":
            if not self.legs or len(self.legs) < 2:
                raise ValueError("multi_city requires at least 2 legs.")
            if len(self.legs) > MAX_LEGS:
                raise ValueError(f"multi_city allows at most {MAX_LEGS} legs.")
            # Overall endpoints/date are derived from the chain (legs are already upper-cased).
            self.origin = self.legs[0].origin
            self.destination = self.legs[-1].destination
            self.departure_date = self.legs[0].date
            self.return_date = None
            self.depart_flex_days = 0
            self.return_flex_days = 0
            return self

        # one_way / round_trip: the flat endpoints are required.
        if not self.origin or not self.destination or self.departure_date is None:
            raise ValueError("origin, destination, and departure_date are required.")
        self.origin = self.origin.upper()
        self.destination = self.destination.upper()
        self.legs = None
        if self.trip_type == "round_trip":
            if self.return_date is None:
                raise ValueError("return_date is required for a round_trip.")
            if self.return_date < self.departure_date:
                raise ValueError("return_date must not be before departure_date.")
        else:
            self.return_date = None
            self.return_flex_days = 0
        return self

    @property
    def resolved_legs(self) -> list[TripLeg]:
        """Normalize any trip shape into the ordered list of legs to price."""
        if self.trip_type == "multi_city" and self.legs:
            return self.legs
        legs = [TripLeg(
            origin=self.origin, destination=self.destination,
            date=self.departure_date, flex_days=self.depart_flex_days,
        )]
        if self.trip_type == "round_trip" and self.return_date is not None:
            legs.append(TripLeg(
                origin=self.destination, destination=self.origin,
                date=self.return_date, flex_days=self.return_flex_days,
            ))
        return legs


class Watch(WatchCreate):
    """A persisted watch. Identity + lifecycle on top of the user's input."""

    id: str = Field(..., description="Stable watch id (uuid4).")
    active: bool = Field(True, description="Whether the scheduler (Slice 3) should poll it.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
    # Slice 8 — ownership: the signed-in user who created the watch. Server-assigned
    # (never client input). None on legacy pre-Slice-8 watches → visible to the admin only.
    owner_email: str | None = Field(None, description="Email of the user who owns this watch.")


class SnapshotLeg(BaseModel):
    """The cheapest priced leg within a snapshot (Slice 9 — per-leg breakdown)."""

    origin: str
    destination: str
    date: _date = Field(..., description="Cheapest date chosen within the leg's flex window.")
    price: float = Field(..., ge=0)
    fare_basis: str | None = None
    carrier: str | None = None


class PriceSnapshot(BaseModel):
    """One observed fare for a watch — a row in the price time-series.

    ``price`` is the *trip total*: the single fare for a one-way watch, the
    outbound+return for a round trip, or the sum of all legs for a multi-city trip.
    Signal detection (Slice 4) reads ``price``, so it works unchanged on every shape.
    ``legs`` (Slice 9) is the canonical per-leg breakdown; ``outbound_*``/``return_*``
    (Slice 7) are kept as convenience fields for the one-way/round-trip cases.
    """

    id: str = Field(..., description="Stable snapshot id (uuid4).")
    watch_id: str = Field(..., description="The watch this observation belongs to.")
    price: float = Field(..., ge=0, description="Trip total (sum of all legs).")
    currency: str
    cabin: str
    fare_basis: str | None = None
    carrier: str | None = None
    provider: str
    observed_at: datetime
    # Slice 9 — canonical per-leg breakdown (one entry per priced leg).
    legs: list[SnapshotLeg] | None = Field(None, description="Per-leg cheapest fares.")
    # Slice 7 — convenience fields for one-way/round-trip (None on legacy snapshots).
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
