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
    """

    fare_provider: str = "mock"
    amadeus_client_id: str | None = None
    amadeus_client_secret: str | None = None
    amadeus_base_url: str = "https://test.api.amadeus.com"
    amadeus_currency: str = "USD"
    request_timeout_s: float = 15.0
    watch_store: str = "sqlite"
    sqlite_path: str = "cheapsawari.db"


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
    )
