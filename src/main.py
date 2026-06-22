"""cheapsawari API — Slice 1: the fare-fetch seam exposed over HTTP.

Run locally:
    uvicorn src.main:app --reload --port 8050

The endpoint is deliberately thin: validate input, call the configured FareProvider,
return a normalized Offer. All the data-source complexity lives behind FareProvider.
"""
from __future__ import annotations

from datetime import date as _date

from fastapi import FastAPI, HTTPException, Path, Query

from .config import get_settings
from .models import Offer, PriceSnapshot, RefreshResult, Watch, WatchCreate
from .providers import ProviderError, get_provider
from .store import WatchNotFoundError, get_repository

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


# --- Slice 2: watches + persistence ---------------------------------------

@app.post("/api/v1/watches", response_model=Watch, status_code=201, tags=["watches"])
def create_watch(data: WatchCreate) -> Watch:
    """Register a route+date to track. 400 if origin == destination."""
    if data.origin.upper() == data.destination.upper():
        raise HTTPException(status_code=400, detail="origin and destination must differ.")
    return get_repository().create_watch(data)


@app.get("/api/v1/watches", response_model=list[Watch], tags=["watches"])
def list_watches(active_only: bool = Query(False, description="Only return active watches.")) -> list[Watch]:
    """List tracked watches, newest first."""
    return get_repository().list_watches(active_only=active_only)


@app.get("/api/v1/watches/{watch_id}", response_model=Watch, tags=["watches"])
def get_watch(watch_id: str = Path(..., description="Watch id.")) -> Watch:
    """Fetch a single watch. 404 if unknown."""
    watch = get_repository().get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.")
    return watch


@app.delete("/api/v1/watches/{watch_id}", status_code=204, tags=["watches"])
def delete_watch(watch_id: str = Path(..., description="Watch id.")) -> None:
    """Delete a watch and its snapshots. 404 if unknown."""
    if not get_repository().delete_watch(watch_id):
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.")


@app.post("/api/v1/watches/{watch_id}/refresh", response_model=RefreshResult, tags=["watches"])
def refresh_watch(watch_id: str = Path(..., description="Watch id.")) -> RefreshResult:
    """Poll a watch once via the active provider and store a snapshot.

    The manual precursor to Slice 3's scheduler — lets a watch accumulate price
    history on demand. 404 if the watch is unknown; 502 on provider error;
    `recorded=false` (200) if the route currently has no inventory.
    """
    repo = get_repository()
    watch = repo.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.")

    try:
        offer = get_provider().get_cheapest_offer(
            watch.origin, watch.destination, watch.departure_date, watch.cabin
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if offer is None:
        return RefreshResult(recorded=False, reason="no inventory")
    snapshot = repo.add_snapshot(watch_id, offer)
    return RefreshResult(recorded=True, snapshot=snapshot)


@app.get(
    "/api/v1/watches/{watch_id}/snapshots",
    response_model=list[PriceSnapshot],
    tags=["watches"],
)
def list_snapshots(
    watch_id: str = Path(..., description="Watch id."),
    limit: int = Query(100, ge=1, le=1000, description="Max snapshots to return."),
) -> list[PriceSnapshot]:
    """Return a watch's price history (newest first). 404 if the watch is unknown."""
    try:
        return get_repository().list_snapshots(watch_id, limit=limit)
    except WatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.") from exc
