"""cheapsawari API — Slice 1: the fare-fetch seam exposed over HTTP.

Run locally:
    uvicorn src.main:app --reload --port 8050

The endpoint is deliberately thin: validate input, call the configured FareProvider,
return a normalized Offer. All the data-source complexity lives behind FareProvider.
"""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timezone
from pathlib import Path as _Path

from fastapi import FastAPI, Header, HTTPException, Path, Query
from fastapi.responses import FileResponse

from .alerts import get_alert_channel
from .config import get_settings
from .models import Offer, PriceSnapshot, RefreshResult, SnapshotCreate, Watch, WatchCreate
from .poll import PollSummary, poll_active_watches
from .providers import ProviderError, get_provider
from .signal import SignalResult, detect_reopening
from .store import WatchNotFoundError, get_repository

app = FastAPI(
    title="cheapsawari API",
    version="0.1.0",
    description="Air flight fare-bucket booking tracker.",
)

# IATA codes are exactly 3 letters. Enforce at the edge so providers can trust input.
_IATA = r"^[A-Za-z]{3}$"

# Single-page dashboard (Slice 5), served from the same app — no separate frontend
# build or hosting, so the whole product stays one $0 Cloud Run service.
_DASHBOARD = _Path(__file__).parent / "web" / "dashboard.html"


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Minimal dashboard: watches, price-history sparklines, and signal badges.

    Static HTML + vanilla JS that calls the JSON API from the same origin. Kept
    out of the OpenAPI schema since it's a UI page, not a contract endpoint.
    """
    return FileResponse(_DASHBOARD, media_type="text/html")


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


@app.post(
    "/api/v1/watches/{watch_id}/snapshots",
    response_model=PriceSnapshot,
    status_code=201,
    tags=["watches"],
)
def record_snapshot(
    data: SnapshotCreate, watch_id: str = Path(..., description="Watch id.")
) -> PriceSnapshot:
    """Manually record an observed fare for a watch (provider='manual').

    Lets you log a price you spotted, or backfill history. 404 if the watch is
    unknown. The cabin defaults to the watch's cabin; observed_at defaults to now.
    """
    repo = get_repository()
    watch = repo.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.")

    offer = Offer(
        origin=watch.origin,
        destination=watch.destination,
        departure_date=watch.departure_date,
        price=data.price,
        currency=data.currency,
        cabin=(data.cabin or watch.cabin).upper(),
        fare_basis=data.fare_basis,
        carrier=data.carrier,
        provider="manual",
        observed_at=data.observed_at or datetime.now(timezone.utc),
    )
    return repo.add_snapshot(watch_id, offer)


# --- Slice 4: signal detection --------------------------------------------

@app.get(
    "/api/v1/watches/{watch_id}/signal",
    response_model=SignalResult,
    tags=["signal"],
)
def get_signal(watch_id: str = Path(..., description="Watch id.")) -> SignalResult:
    """Detect a freshly reopened cheaper bucket in a watch's price history.

    Reads the watch's snapshot series and applies the trailing moving-average
    drop test (defaults: >15% below the 7-day average, rising edge only). 404 if
    the watch is unknown; otherwise `detected` is false when no signal fires.
    """
    repo = get_repository()
    settings = get_settings()
    try:
        snapshots = repo.list_snapshots(watch_id, limit=1000)
    except WatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.") from exc

    signal = detect_reopening(
        snapshots, settings.signal_threshold_pct, settings.signal_window_days
    )
    return SignalResult(watch_id=watch_id, detected=signal is not None, signal=signal)


# --- Slice 3: scheduled polling -------------------------------------------

@app.post("/api/v1/poll", response_model=PollSummary, tags=["poll"])
def run_poll(x_poll_token: str | None = Header(default=None)) -> PollSummary:
    """Poll all active watches once, capped at `POLL_MAX_PER_RUN` (quota protection).

    Intended to be triggered on a schedule (Cloud Scheduler, once/day in prod). If
    `POLL_TOKEN` is configured, a matching `X-Poll-Token` header is required — so a
    public Cloud Run URL can't be hit by anyone to burn the fare-API quota.
    """
    settings = get_settings()
    if settings.poll_token and x_poll_token != settings.poll_token:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Poll-Token.")
    return poll_active_watches(
        get_repository(),
        get_provider(),
        settings.poll_max_per_run,
        alerter=get_alert_channel(settings),
        threshold_pct=settings.signal_threshold_pct,
        window_days=settings.signal_window_days,
    )
