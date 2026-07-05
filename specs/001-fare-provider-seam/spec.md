# Feature Specification: Fare-Provider Seam & Cheapest-Offer Lookup

**Feature Branch**: `retro/001-fare-provider-seam` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 1, 2026-06-21; live-provider migration Amadeus→Travelpayouts, 2026-06-24)

**Input**: retro-spec conversion of Slice 1 (fare-fetch seam) + the 2026-06-24 provider
migration (Travelpayouts/Aviasales replaces the decommissioned Amadeus Self-Service).

## Why

Fare buckets reopen silently; travelers overpay because nobody is watching the exact
moment a cheaper booking class comes back. Everything downstream (watches, snapshots,
signal detection, alerts) needs one normalized answer to "what is the cheapest fare for
route X on date Y?" — without ever coupling to a specific fare API. Slice 1 built that
seam: a `FareProvider` contract returning a provider-agnostic `Offer`, with a
deterministic mock (default; zero quota) so every later slice and the whole Bruno gate
run for free. When Amadeus killed its Self-Service portal, only a new implementation
behind the same seam was needed — Slices 2–5 shipped unchanged.

## User Scenarios & Testing

### User Story 1 - Look up the cheapest fare for a route+date (Priority: P1)

A signed-in user (or any internal caller) asks for the cheapest current offer for
JFK→LAX on a date and gets one normalized `Offer` back.

**Why this priority**: the primitive every other capability composes
(`src/trip.py:56-58` calls it per date; the refresh/poll paths call trip pricing).

**Independent Test**: `GET /api/v1/offers/cheapest?origin=JFK&destination=LAX&date=…`
against the mock provider returns a stable price for the same query every time
(`bruno/cheapsawari/offers/cheapest_deterministic.bru`).

**Acceptance Scenarios**:

1. **Given** the mock provider, **When** the same origin/destination/date/cabin is
   queried twice, **Then** the identical price/fare-basis/carrier is returned (price is
   a pure hash function of the inputs, `src/providers/mock.py:41-50`).
2. **Given** lower-case IATA input, **When** the endpoint runs, **Then** codes are
   normalized to upper case before the provider is called (`src/main.py:250`).
3. **Given** a business-cabin query, **When** priced, **Then** the mock scales the base
   fare by the cabin multiplier (×3.2 for BUSINESS, `src/providers/mock.py:19,44-46`).

---

### User Story 2 - Clean failure semantics (Priority: P1)

Callers can always distinguish "no inventory" from "the upstream is broken" from "bad
input".

**Why this priority**: the seam's contract is what keeps refresh→502 / poll→counted
error handling sane everywhere else (`src/trip.py:15-16`).

**Independent Test**: query the mock's `ZZZ` sentinel route → 404; same-city route →
400; malformed IATA → 422 (`bruno/cheapsawari/offers/no_inventory_404.bru`,
`same_city_400.bru`, `bad_iata_422.bru`).

**Acceptance Scenarios**:

1. **Given** a route with no inventory (mock sentinel `ZZZ`,
   `src/providers/mock.py:32,37-39`), **When** queried, **Then** the provider returns
   `None` and the endpoint answers 404 (`src/main.py:260-264`).
2. **Given** an upstream failure, **When** the provider raises `ProviderError`
   (`src/providers/base.py:10-14`), **Then** the endpoint answers 502 with the message
   (`src/main.py:257-258`).
3. **Given** `origin == destination`, **When** queried, **Then** 400 before any
   provider call (`src/main.py:251-252`).
4. **Given** a non-3-letter code, **When** queried, **Then** FastAPI's pattern
   validation rejects it 422 (`_IATA` regex, `src/main.py:74,240-241`).

---

### User Story 3 - Live fares from Travelpayouts (Priority: P2)

With `FARE_PROVIDER=travelpayouts` and a token, the same endpoint returns real cached
Aviasales prices — the production configuration since 2026-06-24.

**Why this priority**: P2 only because the product works end-to-end on mock; live data
is a config flip, verified in prod (JFK→LAX $365 persisted to Firestore, 2026-06-24).

**Independent Test**: set `FARE_PROVIDER=travelpayouts` + `TRAVELPAYOUTS_TOKEN`, query a
popular route → a real price with `provider: "travelpayouts"` and `fare_basis: null`.

**Acceptance Scenarios**:

1. **Given** a configured token, **When** a route is queried, **Then** the provider GETs
   `/v1/prices/cheap` with the token in the `X-Access-Token` header — never in the URL
   (`src/providers/travelpayouts.py:62-67`).
2. **Given** a response with several tickets, **When** parsed, **Then** the cheapest by
   `price` is selected (`src/providers/travelpayouts.py:92-96`).
3. **Given** the endpoint returns no cached data for the route/date, **When** parsed,
   **Then** `None` (→ 404 / "no inventory"), not an error
   (`src/providers/travelpayouts.py:93-94`).
4. **Given** `FARE_PROVIDER=travelpayouts` but no token, **When** the provider is
   built, **Then** `ProviderError` with an actionable message
   (`src/providers/travelpayouts.py:44-48`).

### Edge Cases

- **`success: false` payload** → `ProviderError` carrying the upstream `error` field
  (`src/providers/travelpayouts.py:87-88`).
- **HTTP/network error** → `httpx.HTTPError` mapped to `ProviderError`
  (`src/providers/travelpayouts.py:70-71`); timeout bounded by `REQUEST_TIMEOUT_S`
  (default 15 s, `src/config.py:57`).
- **Unknown `FARE_PROVIDER` name** → `ProviderError` from the factory
  (`src/providers/factory.py:26-28`).
- **Explicit non-goals**: no itinerary-level/through-fare pricing (each call is one
  route+date); Travelpayouts data is CACHED (~2–7 days of real user searches), not live
  bookable inventory, carries no booking-class code (`fare_basis=None`,
  `src/providers/travelpayouts.py:105`) and does not filter by cabin (the requested
  cabin is recorded for consistency, `src/providers/travelpayouts.py:18-19,104`).

## Requirements

### Functional Requirements

- **FR-001**: Every fare source MUST implement
  `FareProvider.get_cheapest_offer(origin, destination, departure_date, cabin) -> Offer | None`
  and raise `ProviderError` on failure — `None` strictly means "no inventory"
  (`src/providers/base.py:27-45`).
- **FR-002**: Providers MUST return the normalized `Offer` (route, date, price,
  currency, cabin, optional `fare_basis`/`carrier`, `provider` name, `observed_at`
  UTC) and never leak upstream response shapes (`src/models.py:47-72`).
- **FR-003**: The active provider MUST be selected by `FARE_PROVIDER`
  (`mock` default | `travelpayouts` | `amadeus` retained for reference) via the factory
  (`src/providers/factory.py:11-28`; `src/config.py:44,107`).
- **FR-004**: `GET /api/v1/offers/cheapest` MUST validate IATA shape (3 letters),
  reject same-city queries with 400, map `None` to 404 and `ProviderError` to 502, and
  require an authenticated session (`src/main.py:233-265`; auth dependency at 237).
- **FR-005**: The mock provider MUST be deterministic and network-free so contract
  tests are reproducible and burn zero quota (`src/providers/mock.py:22-26,34-62`).
- **FR-006**: The Travelpayouts token MUST be sent as a header, and the currency
  requested per `TRAVELPAYOUTS_CURRENCY` (default `usd`)
  (`src/providers/travelpayouts.py:59,65`; `src/config.py:52,113`).
- **FR-007**: `GET /health` MUST expose the active provider name (mock vs live is
  operationally visible) (`src/main.py:112-120`).
- **Superseded**: Amadeus-specific behavior (OAuth2 client-credentials, per-API quota
  budget) is NOT current behavior — see research.md Decision 4; the implementation is
  retained for reference only (`src/providers/amadeus.py:1-18`;
  `src/providers/factory.py:23-25`).

### Key Entities

- **Offer**: the canonical observed fare — the record everything downstream snapshots
  (`src/models.py:47-72`; full shape in data-model.md).
- **FareProvider / ProviderError**: the seam contract (`src/providers/base.py`).

## Success Criteria

- **SC-001**: Bruno `offers/` suite green — 7 requests covering health, deterministic
  pricing, lower-case normalization, business cabin, 404/400/422 paths
  (`bruno/cheapsawari/offers/`); part of the full 97 req / 242 assert gate.
- **SC-002**: Slices 2–9 shipped **without touching the seam callers** when the live
  provider changed — the migration updated only `config.py`, `factory.py`, and added
  `travelpayouts.py` (Project_Structure.md changelog row 2026-06-24).
- **SC-003**: Live verification: prod flipped to `FARE_PROVIDER=travelpayouts`
  2026-06-24 and a real JFK→LAX fare ($365) was persisted to Firestore
  (`docs/DEPLOYMENT.md:15-16`).

## Assumptions

- A Travelpayouts affiliate account exists and its Data-API token is set in the
  environment (`.env.example` TRAVELPAYOUTS_TOKEN); without it, prod would fall back to
  mock by config choice.
- Cached price-trend data is acceptable for a *tracker* (the product alerts on drops;
  it does not promise a bookable quote) — the tradeoff is documented in code
  (`src/providers/travelpayouts.py:7-19`).
- Free tier posture: Travelpayouts has no per-call charge; the daily poll volume is
  well inside polite use (`docs/DEPLOYMENT.md:86-90`).
