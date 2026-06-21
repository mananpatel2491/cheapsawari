"""Provider selection — resolves the configured FareProvider from settings."""
from __future__ import annotations

from ..config import Settings, get_settings
from .base import FareProvider, ProviderError
from .amadeus import AmadeusFareProvider
from .mock import MockFareProvider


def get_provider(settings: Settings | None = None) -> FareProvider:
    """Return the FareProvider named by ``FARE_PROVIDER`` (default 'mock').

    Raises:
        ProviderError: If the configured provider name is unknown.
    """
    settings = settings or get_settings()
    name = settings.fare_provider
    if name == "mock":
        return MockFareProvider()
    if name == "amadeus":
        return AmadeusFareProvider(settings)
    raise ProviderError(f"Unknown FARE_PROVIDER '{name}' (expected 'mock' or 'amadeus').")
