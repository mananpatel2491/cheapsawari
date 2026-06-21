"""cheapsawari API — Slice 1: the fare-fetch seam exposed over HTTP.

Run locally:
    uvicorn src.main:app --reload --port 8050

The endpoint is deliberately thin: validate input, call the configured FareProvider,
return a normalized Offer. All the data-source complexity lives behind FareProvider.
"""
from __future__ import annotations

from datetime import date as _date

from fastapi import FastAPI, HTTPException, Query

from .config import get_settings
from .models import Offer
from .providers import ProviderError, get_provider

app = FastAPI(
    title="cheapsawari API",
    version="0.1.0",
    description="Air flight fare-bucket booking tracker — Slice 1: fare-fetch seam.",
)

# IATA codes are exactly 3 letters. Enforce at the edge so providers can trust input.
_IATA = r"^[A-Za-z]{3}$"


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe + the active provider (handy for confirming mock vs amadeus)."""
    return {"status": "ok", "provider": get_settings().fare_provider}


@app.get("/api/v1/offers/cheapest", response_model=Offer, tags=["offers"])
def cheapest_offer(
    origin: str = Query(..., pattern=_IATA, description="Origin IATA code, e.g. JFK."),
    destination: str = Query(..., pattern=_IATA, description="Destination IATA code, e.g. LAX."),
    date: _date = Query(..., description="Departure date (YYYY-MM-DD)."),
    cabin: str = Query("ECONOMY", description="Cabin class."),
) -> Offer:
    """Return the cheapest current offer for a route+date.

    404 if the route has no inventory; 502 if the upstream provider failed;
    400 if origin and destination are identical.
    """
    origin, destination = origin.upper(), destination.upper()
    if origin == destination:
        raise HTTPException(status_code=400, detail="origin and destination must differ.")

    provider = get_provider()
    try:
        offer = provider.get_cheapest_offer(origin, destination, date, cabin)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if offer is None:
        raise HTTPException(
            status_code=404,
            detail=f"No offers for {origin}->{destination} on {date.isoformat()}.",
        )
    return offer
