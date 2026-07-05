# Research: Fare-Provider Seam & Cheapest-Offer Lookup

As-built record — decisions reconstructed 2026-07-05 from Slice 1 / migration changelog
rows (Project_Structure.md), `PATTERNS.md`, and provider docstrings.

## Decision 1 — A provider seam before any provider

**Choice**: define `FareProvider` + normalized `Offer` first; the API and all later
slices depend only on the contract (`src/providers/base.py:17-45`; `src/models.py:1-6`).
**Why**: fare APIs are volatile (quota, pricing, existence — proven when Amadeus died);
decoupling was the product's survival trait.
**Rejected**: calling a vendor SDK directly from the endpoint (couples every downstream
slice to one vendor's shape).

## Decision 2 — Deterministic mock as the DEFAULT provider

**Choice**: `FARE_PROVIDER` defaults to `mock`; the price is a pure SHA-256 function of
(origin, destination, date, cabin) with a fare-basis ring and pseudo-carrier
(`src/providers/mock.py:18-26,41-50`; `src/config.py:44`).
**Why**: contract tests need reproducible numbers; local dev must never burn live
quota; the `ZZZ` sentinel makes the 404 path testable (`src/providers/mock.py:32`).
**Rejected**: random/mutable fixtures (non-reproducible Bruno assertions), live-by-default
(quota burn, network-dependent tests).

## Decision 3 — Errors ≠ empty: `ProviderError` vs `None`

**Choice**: `None` = no inventory (→404); `ProviderError` = could-not-answer (→502)
(`src/providers/base.py:10-14,40-44`; `src/main.py:256-264`).
**Why**: the poll engine must count failures without aborting and must not mask an
outage as "no fares" (`src/poll.py:79-87`; `src/trip.py:51-53`).

## Decision 4 — SUPERSEDED: Amadeus Self-Service as the live source

**Choice (original, Slice 1)**: Amadeus Flight Offers Search behind the seam — OAuth2
client-credentials, in-process token cache, per-API free quota that sized
`POLL_MAX_PER_RUN` (`src/providers/amadeus.py:1-18`).
**Superseded (2026-06-24)**: Amadeus discontinued the Self-Service portal
(decommissioned 2026-07-17; signups already paused) — the free path died before launch.
The implementation is retained for reference only, the factory branch marked deprecated
(`src/providers/factory.py:23-25`), and `.env.example` labels the creds DEPRECATED.
Amadeus behavior is **not** current behavior anywhere in these specs.

## Decision 5 — Travelpayouts/Aviasales `/v1/prices/cheap` as the replacement

**Choice**: free Data API, affiliate-token gated (`X-Access-Token` header), returning
CACHED cheapest-price-by-route data (`src/providers/travelpayouts.py:1-26,37`).
**Why**: keeps the ~$0/mo posture with real prices; a *tracker* needs trend data, not
guaranteed bookable quotes. Honest tradeoffs are written into the module: cached ~2–7
days, no booking-class code (`fare_basis=None` → the "bucket reopened" signal becomes
"cheapest price dropped"; detection is price-based and unaffected), cabin not filtered
(`src/providers/travelpayouts.py:7-19,105`).
**Rejected**: paid APIs (breaks the $0 constitution gate — Director arbitration would
be required), scraping (fragile, ToS risk).
**Consequence for UX**: cache is sparse for quiet routes/far-out dates — popular routes
(JFK→LAX) return data, quiet ones (DTW⇄AMD) may return nothing until searched by real
users; surfaced verbatim in the dashboard's refresh message (spec 006).

## Decision 6 — Pure `_parse()` for testability

**Choice**: response mapping is a side-effect-free method validated against the
documented response schema (`src/providers/travelpayouts.py:76-108`).
**Why**: the live API needed to be verifiable before the owner's token existed
(migration shipped with prod still on mock; live flip + verification followed on
2026-06-24).
