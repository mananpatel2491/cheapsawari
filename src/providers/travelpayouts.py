"""Travelpayouts (Aviasales) fare provider.

Wraps the Travelpayouts Flight Data API `/v1/prices/cheap` endpoint behind the
FareProvider seam. Chosen as the live data source after Amadeus discontinued its
Self-Service portal (decommissioned 2026-07-17).

WHAT IT IS (and the honest tradeoffs):
    - Free: access is gated only by an affiliate token (TRAVELPAYOUTS_TOKEN), no
      per-call charge — so the tracker stays ~$0/mo.
    - CACHED, not live: prices come from recent user searches and are stored ~2–7
      days. This is fare-*trend* data, not real-time bookable inventory. That suits a
      "watch the price and tell me when it drops" tracker, but a quote here is not a
      guaranteed bookable fare.
    - NO fare-basis / booking class: this endpoint returns a cheapest price, not the
      inventory bucket code. So `fare_basis` is always None, and the "bucket reopened"
      signal effectively means "cheapest observed price dropped" — still exactly the
      signal we snapshot and alert on (detection is price-based, unaffected).
    - Cabin is NOT filtered by this endpoint (it returns the cheapest available,
      typically economy); we record the requested cabin for consistency.

AUTH:
    Token in the `X-Access-Token` header (kept out of the URL/query logs). Get it from
    the Travelpayouts dashboard after signing up; set TRAVELPAYOUTS_TOKEN in .env.

Docs: https://travelpayouts.github.io/slate/ ( /v1/prices/cheap ).
"""
from __future__ import annotations

from datetime import date as _date

import httpx

from ..config import Settings
from ..models import Offer
from .base import FareProvider, ProviderError

_BASE_URL = "https://api.travelpayouts.com"


class TravelpayoutsFareProvider(FareProvider):
    name = "travelpayouts"

    def __init__(self, settings: Settings) -> None:
        if not settings.travelpayouts_token:
            raise ProviderError(
                "Travelpayouts token missing: set TRAVELPAYOUTS_TOKEN "
                "(or use FARE_PROVIDER=mock)."
            )
        self._settings = settings

    # --- query --------------------------------------------------------------
    def get_cheapest_offer(
        self, origin: str, destination: str, departure_date: _date, cabin: str = "ECONOMY"
    ) -> Offer | None:
        params = {
            "origin": origin,
            "destination": destination,
            "depart_date": departure_date.isoformat(),  # yyyy-mm-dd is accepted
            "currency": self._settings.travelpayouts_currency,
        }
        try:
            resp = httpx.get(
                f"{_BASE_URL}/v1/prices/cheap",
                params=params,
                headers={"X-Access-Token": self._settings.travelpayouts_token},
                timeout=self._settings.request_timeout_s,
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Travelpayouts request failed: {exc}") from exc

        return self._parse(payload, origin, destination, departure_date, cabin)

    # --- parsing (pure; unit-testable without the network) ------------------
    def _parse(
        self, payload: dict, origin: str, destination: str, departure_date: _date, cabin: str
    ) -> Offer | None:
        """Map a /v1/prices/cheap response to the cheapest Offer, or None.

        Response shape:
            {"success": true,
             "data": {"<DEST>": {"0": {"price":.., "airline":.., "flight_number":..,
                                       "departure_at":.., "return_at":.., "expires_at":..}, ...}},
             "error": null}
        """
        if not payload.get("success", False):
            raise ProviderError(f"Travelpayouts error: {payload.get('error') or 'unknown'}")

        # data is keyed by destination IATA, then by an index string.
        entries = (payload.get("data") or {}).get(destination.upper()) or {}
        tickets = [t for t in entries.values() if isinstance(t, dict) and "price" in t]
        if not tickets:
            return None  # no cached inventory for this route/date → caller maps to 404

        cheapest = min(tickets, key=lambda t: float(t["price"]))
        airline = cheapest.get("airline")
        return Offer(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            price=float(cheapest["price"]),
            currency=self._settings.travelpayouts_currency.upper(),
            cabin=cabin.upper(),
            fare_basis=None,  # endpoint exposes no booking-class / bucket code
            carrier=airline or None,
            provider=self.name,
        )
