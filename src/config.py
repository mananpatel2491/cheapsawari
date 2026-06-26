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
    # Travelpayouts (Aviasales) — the live provider after Amadeus Self-Service shut down.
    # Free, affiliate-token gated; returns cached cheapest-price-by-route data.
    travelpayouts_token: str | None = None
    travelpayouts_currency: str = "usd"
    # Affiliate marker (Slice 18) — the public Travelpayouts/Aviasales affiliate id used
    # to build "book this fare" deep links. Not a secret (it appears in public URLs);
    # optional — links still work without it, just without affiliate attribution.
    travelpayouts_marker: str | None = None
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
    # --- Slice 16: email notifications (stdlib SMTP; Gmail-ready, ~$0) ---
    # Set ALERT_CHANNEL=email to deliver reopened-bucket alerts to each watch owner's
    # email. For Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USER=<the gmail>,
    # SMTP_PASSWORD=<a 16-char App Password> (needs 2FA on the account), ALERT_EMAIL_FROM=
    # <the gmail>. ALERT_EMAIL_TO is an optional fallback recipient when a watch has no
    # owner_email. If SMTP is unconfigured, the channel degrades to log (alerts still
    # surface, just aren't emailed). app_base_url is linked in the email body.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    alert_email_from: str | None = None
    alert_email_to: str | None = None
    app_base_url: str = "https://cheapsawari.web.app"
    # --- Slice 6: auth + admin (Google Identity Services) ---
    # auth_mode: "google" (prod; "Sign in with Google", verifies the Google ID token) or
    #   "dev" (local/tests; a passwordless email login so the gate is exercisable without
    #   a real OAuth client). The dev login endpoint is hard-disabled unless auth_mode=="dev".
    # google_client_id: OAuth 2.0 Web client id; the audience the ID token is verified against
    #   (required when auth_mode=="google").
    # admin_email: the bootstrap owner — always allowed and the only account that can manage
    #   the allowlist. Stored/compared lower-cased.
    # session_secret: signing key for the HttpOnly session cookie (Starlette SessionMiddleware).
    #   MUST be set to a stable random value in prod or sessions break across instances/restarts.
    auth_mode: str = "dev"
    google_client_id: str | None = None
    admin_email: str = "mpatel.mi24@gmail.com"
    session_secret: str = "dev-insecure-session-secret-change-me"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings from the environment. Cached so it's parsed once per process."""
    return Settings(
        fare_provider=os.getenv("FARE_PROVIDER", "mock").strip().lower(),
        amadeus_client_id=os.getenv("AMADEUS_CLIENT_ID"),
        amadeus_client_secret=os.getenv("AMADEUS_CLIENT_SECRET"),
        amadeus_base_url=os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com").rstrip("/"),
        amadeus_currency=os.getenv("AMADEUS_CURRENCY", "USD"),
        travelpayouts_token=os.getenv("TRAVELPAYOUTS_TOKEN") or None,
        travelpayouts_currency=os.getenv("TRAVELPAYOUTS_CURRENCY", "usd").strip().lower(),
        travelpayouts_marker=os.getenv("TRAVELPAYOUTS_MARKER") or None,
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
        smtp_host=os.getenv("SMTP_HOST") or None,
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER") or None,
        smtp_password=os.getenv("SMTP_PASSWORD") or None,
        smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").strip().lower() != "false",
        alert_email_from=os.getenv("ALERT_EMAIL_FROM") or None,
        alert_email_to=os.getenv("ALERT_EMAIL_TO") or None,
        app_base_url=os.getenv("APP_BASE_URL", "https://cheapsawari.web.app").rstrip("/"),
        auth_mode=os.getenv("AUTH_MODE", "dev").strip().lower(),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID") or None,
        admin_email=os.getenv("ADMIN_EMAIL", "mpatel.mi24@gmail.com").strip().lower(),
        session_secret=os.getenv("SESSION_SECRET", "dev-insecure-session-secret-change-me"),
    )
