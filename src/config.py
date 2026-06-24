"""Application configuration, loaded from the environment (.env supported).

Centralizes all tunables so providers and the app never read os.environ directly.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from the project root once, on import. Values already present in the
# real environment win over .env (override=False), matching 12-factor behavior.
load_dotenv(override=False)


class Settings(BaseModel):
    """Resolved runtime settings.

    Attributes:
        fare_provider: Which FareProvider implementation to use ("mock" | "amadeus").
            Defaults to "mock" so tests and local dev never burn the live API quota.
        amadeus_client_id: Amadeus Self-Service OAuth2 client id (required for amadeus).
        amadeus_client_secret: Amadeus Self-Service OAuth2 client secret.
        amadeus_base_url: Amadeus API base. Defaults to the test environment; switch to
            https://api.amadeus.com for production once a paid/keyed plan is in place.
        amadeus_currency: Currency to request offers in.
        request_timeout_s: Per-call HTTP timeout for outbound provider requests.
        watch_store: Which WatchRepository to use ("sqlite" | "firestore"). Defaults to
            "sqlite" — local, durable, zero-dependency, hermetic for tests. "firestore"
            is wired at Slice 3 (cloud).
        sqlite_path: Filesystem path for the SQLite store (when watch_store == "sqlite").
        poll_max_per_run: Hard cap on how many active watches a single poll run will
            query. Amadeus Self-Service free quotas are per-API and vary (~200–10k/mo;
            confirm the Flight Offers Search figure in your Workspace), so size this to
            fit. Budget math: poll_max_per_run × runs_per_day × 30 must stay < quota.
            Default 60 is a placeholder until the real quota is confirmed.
        poll_token: Optional shared secret. If set, POST /api/v1/poll requires a matching
            `X-Poll-Token` header (so a public Cloud Run URL can't be abused to burn quota).
            If unset (local/dev), the endpoint is open.
    """

    fare_provider: str = "mock"
    amadeus_client_id: str | None = None
    amadeus_client_secret: str | None = None
    amadeus_base_url: str = "https://test.api.amadeus.com"
    amadeus_currency: str = "USD"
    request_timeout_s: float = 15.0
    watch_store: str = "sqlite"
    sqlite_path: str = "cheapsawari.db"
    gcp_project: str | None = None
    poll_max_per_run: int = 60
    poll_token: str | None = None
    # --- Slice 4: signal detection + alerts ---
    # alert_channel: "log" (default; zero-cost, prod-safe) or "webhook".
    # alert_webhook_url: target for the webhook channel (Slack/Discord/generic incoming hook).
    # signal_threshold_pct: drop below the trailing average that counts as a reopened bucket.
    # signal_window_days: length of the trailing moving-average window.
    alert_channel: str = "log"
    alert_webhook_url: str | None = None
    signal_threshold_pct: float = 15.0
    signal_window_days: int = 7


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings from the environment. Cached so it's parsed once per process."""
    return Settings(
        fare_provider=os.getenv("FARE_PROVIDER", "mock").strip().lower(),
        amadeus_client_id=os.getenv("AMADEUS_CLIENT_ID"),
        amadeus_client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
        amadeus_base_url=os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com").rstrip("/"),
        amadeus_currency=os.getenv("AMADEUS_CURRENCY", "USD"),
        request_timeout_s=float(os.getenv("REQUEST_TIMEOUT_S", "15.0")),
        watch_store=os.getenv("WATCH_STORE", "sqlite").strip().lower(),
        sqlite_path=os.getenv("SQLITE_PATH", "cheapsawari.db"),
        # Cloud Run sets GOOGLE_CLOUD_PROJECT; locally falls back to GCP_PROJECT or ADC inference.
        gcp_project=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or None,
        poll_max_per_run=int(os.getenv("POLL_MAX_PER_RUN", "60")),
        poll_token=os.getenv("POLL_TOKEN") or None,
        alert_channel=os.getenv("ALERT_CHANNEL", "log").strip().lower(),
        alert_webhook_url=os.getenv("ALERT_WEBHOOK_URL") or None,
        signal_threshold_pct=float(os.getenv("SIGNAL_THRESHOLD_PCT", "15.0")),
        signal_window_days=int(os.getenv("SIGNAL_WINDOW_DAYS", "7")),
    )
