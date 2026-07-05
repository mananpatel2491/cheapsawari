---
description: "As-built task record for the fare-provider seam + cheapest-offer lookup"
---

# Tasks: Fare-Provider Seam & Cheapest-Offer Lookup

As-built record — reconstructed 2026-07-05 from Slice 1 (changelog 2026-06-21) and the
provider migration (changelog 2026-06-24). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Contract + domain model

- [X] T001 `src/providers/base.py`: `FareProvider` ABC (`get_cheapest_offer`), `name`
  attribute, `ProviderError` with None-vs-error semantics (Slice 1)
- [X] T002 [P] `src/models.py`: normalized `Offer` model with `fare_basis` ("the
  bucket") central to the product thesis (Slice 1)
- [X] T003 [P] `src/config.py`: env-driven `Settings` + `get_settings()` lru_cache;
  `FARE_PROVIDER`, Amadeus creds, `REQUEST_TIMEOUT_S` (Slice 1)

## Phase 2: Providers (US1, US2)

- [X] T004 [US1] `src/providers/mock.py`: SHA-256-seeded deterministic pricing, cabin
  multipliers, fare-basis ring, `ZZZ` no-inventory sentinel (Slice 1)
- [X] T005 `src/providers/amadeus.py`: OAuth2 client-credentials + token cache + Flight
  Offers Search mapping (Slice 1; SUPERSEDED 2026-06-24 — retained for reference)
- [X] T006 `src/providers/factory.py`: `get_provider()` resolving `FARE_PROVIDER`
  (Slice 1; travelpayouts branch + amadeus deprecation note 2026-06-24)

## Phase 3: Endpoint (US1, US2)

- [X] T007 [US1] `src/main.py` `GET /api/v1/offers/cheapest`: IATA pattern validation,
  upper-casing, 400 same-city, 404 no-inventory, 502 ProviderError (Slice 1; auth
  dependency added Slice 6)
- [X] T008 [US1] `GET /health` liveness + active-provider field (Slice 1)
- [X] T009 Bruno `offers/` suite: 7 requests / 24 assertions (health, deterministic,
  lowercase, business cabin, 404/400/422) (Slice 1)

## Phase 4: Live-provider migration (US3)

- [X] T010 [US3] `src/providers/travelpayouts.py`: `/v1/prices/cheap` client with
  header-token auth, pure `_parse()` (cheapest-of-many, no-inventory→None,
  error→ProviderError), documented cached-data tradeoffs (2026-06-24)
- [X] T011 [US3] `src/config.py` + `.env.example`: `TRAVELPAYOUTS_TOKEN/CURRENCY`;
  Amadeus keys marked DEPRECATED (2026-06-24)
- [X] T012 [US3] Prod flip: `FARE_PROVIDER=travelpayouts` on Cloud Run rev
  `cheapsawari-api-00004-kht`; live JFK→LAX $365 persisted to Firestore (2026-06-24)

## Open follow-ups (genuinely pending)

- [ ] T013 Optional itinerary-level provider (true through-fares / bookable quotes) —
  only if later needed (Project_Structure.md roadmap "Next (planned)")
- [ ] T014 Config docstring drift: `src/config.py:22` still describes `fare_provider`
  as `"mock" | "amadeus"` — update to include `travelpayouts` (doc-only)
