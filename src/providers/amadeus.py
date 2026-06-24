"""Amadeus Self-Service fare provider.

Wraps the Amadeus Flight Offers Search API behind the FareProvider seam.

QUOTA (the design constraint that shapes the whole tracker):
    Self-Service free quotas are PER-API and vary (~200–10,000 calls/month depending
    on the endpoint) — there is no single flat number; confirm the live Flight Offers
    Search quota in your Amadeus account Workspace. Beyond it you get 429 in test, or
    pay-per-call in production. Each get_cheapest_offer() call = 1 OAuth token reuse +
    1 search request. Slice 3's scheduler therefore caps polls/day across all active
    watches (POLL_MAX_PER_RUN); set that cap to fit your confirmed quota. The mock
    provider is the default precisely so tests never spend this budget. NOTE: the test
    environment also serves limited/cached data, not full live inventory.

AUTH:
    OAuth2 client-credentials. Set AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET in .env.
    Tokens are cached in-process until shortly before expiry to avoid re-authing per call.
"""
from __future__ import annotations

import time
from datetime import date as _date

import httpx

from ..config import Settings
from ..models import Offer
from .base import FareProvider, ProviderError


class AmadeusFareProvider(FareProvider):
    name = "amadeus"

    def __init__(self, settings: Settings) -> None:
        if not settings.amadeus_client_id or not settings.amadeus_client_secret:
            raise ProviderError(
                "Amadeus credentials missing: set AMADEUS_CLIENT_ID and "
                "AMADEUS_CLIENT_SECRET (or use FARE_PROVIDER=mock)."
            )
        self._settings = settings
        self._token: str | None = None
        self._token_expiry: float = 0.0  # epoch seconds

    # --- auth ---------------------------------------------------------------
    def _access_token(self) -> str:
        # Reuse the cached token until 30s before it expires.
        if self._token and time.time() < self._token_expiry - 30:
            return self._token

        url = f"{self._settings.amadeus_base_url}/v1/security/oauth2/token"
        try:
            resp = httpx.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._settings.amadeus_client_id,
                    "client_secret": self._settings.amadeus_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._settings.request_timeout_s,
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Amadeus auth failed: {exc}") from exc

        self._token = payload["access_token"]
        self._token_expiry = time.time() + int(payload.get("expires_in", 1799))
        return self._token

    # --- query --------------------------------------------------------------
    def get_cheapest_offer(
        self, origin: str, destination: str, departure_date: _date, cabin: str = "ECONOMY"
    ) -> Offer | None:
        url = f"{self._settings.amadeus_base_url}/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date.isoformat(),
            "adults": 1,
            "currencyCode": self._settings.amadeus_currency,
            "travelClass": cabin.upper(),
            "max": 5,
        }
        try:
            resp = httpx.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                timeout=self._settings.request_timeout_s,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except httpx.HTTPError as exc:
            raise ProviderError(f"Amadeus search failed: {exc}") from exc

        if not data:
            return None

        cheapest = min(data, key=lambda o: float(o["price"]["grandTotal"]))
        return self._normalize(cheapest, origin, destination, departure_date, cabin)

    # --- normalization ------------------------------------------------------
    def _normalize(
        self, raw: dict, origin: str, destination: str, departure_date: _date, cabin: str
    ) -> Offer:
        price_block = raw.get("price", {})
        # fareDetailsBySegment carries the real booking class / fare basis (the "bucket").
        fare_basis = None
        observed_cabin = cabin.upper()
        traveler = (raw.get("travelerPricings") or [{}])[0]
        seg_details = (traveler.get("fareDetailsBySegment") or [{}])[0]
        fare_basis = seg_details.get("fareBasis") or seg_details.get("class")
        observed_cabin = seg_details.get("cabin", observed_cabin)

        carriers = raw.get("validatingAirlineCodes") or []
        carrier = carriers[0] if carriers else None

        return Offer(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            price=float(price_block.get("grandTotal", price_block.get("total", 0.0))),
            currency=price_block.get("currency", self._settings.amadeus_currency),
            cabin=observed_cabin,
            fare_basis=fare_basis,
            carrier=carrier,
            provider=self.name,
        )
