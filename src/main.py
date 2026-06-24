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

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from . import auth
from .alerts import get_alert_channel
from .config import get_settings
from .models import (
    AddUserRequest,
    AllowedUser,
    Offer,
    PriceSnapshot,
    RefreshResult,
    SessionUser,
    SnapshotCreate,
    Watch,
    WatchCreate,
)
from .poll import PollSummary, poll_active_watches
from .providers import ProviderError, get_provider
from .signal import SignalResult, detect_reopening
from .store import WatchNotFoundError, get_repository
from .users import get_user_repository

app = FastAPI(
    title="cheapsawari API",
    version="0.2.0",
    description="Air flight fare-bucket booking tracker.",
)

# Signs an HttpOnly session cookie (Slice 6 auth). The secret must be stable across
# instances/restarts in prod (set SESSION_SECRET) or sessions silently invalidate.
app.add_middleware(
    SessionMiddleware,
    secret_key=get_settings().session_secret,
    https_only=False,  # Cloud Run terminates TLS at the proxy; the app sees http internally.
    same_site="lax",
)

# IATA codes are exactly 3 letters. Enforce at the edge so providers can trust input.
_IATA = r"^[A-Za-z]{3}$"

# Single-page UI (Slice 5/6), served from the same app — no separate frontend build
# or hosting, so the whole product stays one $0 Cloud Run service.
_WEB = _Path(__file__).parent / "web"
_DASHBOARD = _WEB / "dashboard.html"
_LOGIN = _WEB / "login.html"
_ADMIN = _WEB / "admin.html"


@app.get("/", include_in_schema=False, response_model=None)
def dashboard(request: Request) -> FileResponse | RedirectResponse:
    """Minimal dashboard: watches, price-history sparklines, and signal badges.

    Gated (Slice 6): unauthenticated visitors are redirected to the login page so the
    landing URL never leaks tracked routes. Static HTML + vanilla JS that calls the
    JSON API from the same origin. Out of the OpenAPI schema — it's a UI page.
    """
    if auth.current_user(request) is None:
        return RedirectResponse("/login", status_code=302)
    return FileResponse(_DASHBOARD, media_type="text/html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    """Sign-in page. Renders "Sign in with Google" (or a dev email form in AUTH_MODE=dev)."""
    return FileResponse(_LOGIN, media_type="text/html")


@app.get("/admin", include_in_schema=False, response_model=None)
def admin_page(request: Request) -> FileResponse | RedirectResponse:
    """Admin console (allowlist management). Redirects non-signed-in visitors to login;
    the page itself enforces admin-only via /api/v1/auth/me and the admin API returns 403."""
    if auth.current_user(request) is None:
        return RedirectResponse("/login", status_code=302)
    return FileResponse(_ADMIN, media_type="text/html")


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness probe + the active provider (handy for confirming mock vs amadeus)."""
    return {"status": "ok", "provider": get_settings().fare_provider}


# --- Slice 6: auth + admin -------------------------------------------------

@app.get("/api/v1/auth/config", tags=["auth"])
def auth_config() -> dict:
    """Public: what the login page needs to render the right control (no secrets)."""
    settings = get_settings()
    return {"mode": settings.auth_mode, "google_client_id": settings.google_client_id}


@app.get("/api/v1/auth/me", response_model=SessionUser, tags=["auth"])
def auth_me(user: SessionUser = Depends(auth.require_user)) -> SessionUser:
    """Return the signed-in user (email + is_admin). 401 if not authenticated/allowed."""
    return user


@app.post("/api/v1/auth/google", response_model=SessionUser, tags=["auth"])
def auth_google(request: Request, body: dict) -> SessionUser:
    """Verify a Google ID token, check the allowlist, and open a session.

    Body: `{"credential": "<google id token>"}`. 401 if the token is invalid or the
    account isn't allowed (the admin is always allowed; others must be on the allowlist).
    """
    credential = (body or {}).get("credential")
    if not credential:
        raise HTTPException(status_code=400, detail="Missing 'credential'.")
    try:
        email = auth.verify_google_credential(credential)
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if not auth.is_access_allowed(email):
        raise HTTPException(status_code=403, detail=f"{email} is not on the allowlist.")
    auth.login_session(request, email)
    return SessionUser(email=email, is_admin=auth.is_admin(email))


@app.post("/api/v1/auth/dev", response_model=SessionUser, tags=["auth"])
def auth_dev(request: Request, body: dict) -> SessionUser:
    """Dev-only passwordless login (AUTH_MODE=dev). 404 in any other mode.

    Lets the gate be exercised locally and by the Bruno suite without a real OAuth client.
    Still allowlist-gated, so it grants no access the admin hasn't configured.
    """
    if get_settings().auth_mode != "dev":
        raise HTTPException(status_code=404, detail="Not found.")
    email = ((body or {}).get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid 'email' is required.")
    if not auth.is_access_allowed(email):
        raise HTTPException(status_code=403, detail=f"{email} is not on the allowlist.")
    auth.login_session(request, email)
    return SessionUser(email=email, is_admin=auth.is_admin(email))


@app.post("/api/v1/auth/logout", status_code=204, tags=["auth"])
def auth_logout(request: Request) -> None:
    """End the session (clears the cookie)."""
    auth.logout_session(request)


@app.get("/api/v1/admin/users", response_model=list[AllowedUser], tags=["admin"])
def admin_list_users(_: SessionUser = Depends(auth.require_admin)) -> list[AllowedUser]:
    """List the allowlist (admin only). The admin owner is implicit and not shown here."""
    return get_user_repository().list_users()


@app.post("/api/v1/admin/users", response_model=AllowedUser, status_code=201, tags=["admin"])
def admin_add_user(
    data: AddUserRequest, admin: SessionUser = Depends(auth.require_admin)
) -> AllowedUser:
    """Grant a Gmail address access (admin only). Idempotent. 400 on a malformed email."""
    email = data.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email is required.")
    if auth.is_admin(email):
        raise HTTPException(status_code=400, detail="The owner already has access.")
    return get_user_repository().add_user(email, added_by=admin.email)


@app.delete("/api/v1/admin/users/{email}", status_code=204, tags=["admin"])
def admin_remove_user(
    email: str = Path(..., description="Email to revoke."),
    _: SessionUser = Depends(auth.require_admin),
) -> None:
    """Revoke a user's access (admin only). 400 if you try to remove the owner; 404 if unknown."""
    email = email.strip().lower()
    if auth.is_admin(email):
        raise HTTPException(status_code=400, detail="The owner cannot be removed.")
    if not get_user_repository().remove_user(email):
        raise HTTPException(status_code=404, detail=f"'{email}' is not on the allowlist.")


@app.get(
    "/api/v1/offers/cheapest",
    response_model=Offer,
    tags=["offers"],
    dependencies=[Depends(auth.require_user)],
)
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

@app.post(
    "/api/v1/watches",
    response_model=Watch,
    status_code=201,
    tags=["watches"],
    dependencies=[Depends(auth.require_user)],
)
def create_watch(data: WatchCreate) -> Watch:
    """Register a route+date to track. 400 if origin == destination."""
    if data.origin.upper() == data.destination.upper():
        raise HTTPException(status_code=400, detail="origin and destination must differ.")
    return get_repository().create_watch(data)


@app.get(
    "/api/v1/watches",
    response_model=list[Watch],
    tags=["watches"],
    dependencies=[Depends(auth.require_user)],
)
def list_watches(active_only: bool = Query(False, description="Only return active watches.")) -> list[Watch]:
    """List tracked watches, newest first."""
    return get_repository().list_watches(active_only=active_only)


@app.get(
    "/api/v1/watches/{watch_id}",
    response_model=Watch,
    tags=["watches"],
    dependencies=[Depends(auth.require_user)],
)
def get_watch(watch_id: str = Path(..., description="Watch id.")) -> Watch:
    """Fetch a single watch. 404 if unknown."""
    watch = get_repository().get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.")
    return watch


@app.delete(
    "/api/v1/watches/{watch_id}",
    status_code=204,
    tags=["watches"],
    dependencies=[Depends(auth.require_user)],
)
def delete_watch(watch_id: str = Path(..., description="Watch id.")) -> None:
    """Delete a watch and its snapshots. 404 if unknown."""
    if not get_repository().delete_watch(watch_id):
        raise HTTPException(status_code=404, detail=f"Watch '{watch_id}' not found.")


@app.post(
    "/api/v1/watches/{watch_id}/refresh",
    response_model=RefreshResult,
    tags=["watches"],
    dependencies=[Depends(auth.require_user)],
)
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
    dependencies=[Depends(auth.require_user)],
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
    dependencies=[Depends(auth.require_user)],
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
    dependencies=[Depends(auth.require_user)],
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
