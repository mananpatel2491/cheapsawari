# Implementation Plan: Fare-Provider Seam & Cheapest-Offer Lookup

**Branch**: `retro/001-fare-provider-seam` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slice 1 (2026-06-21) and the Amadeus→Travelpayouts
migration (2026-06-24).

## Summary

An abstract `FareProvider` (`src/providers/base.py`) turns any fare source into a
normalized `Offer` (`src/models.py:47-72`). Three implementations: `MockFareProvider`
(deterministic SHA-256-seeded pricing, default), `TravelpayoutsFareProvider` (live;
Aviasales `/v1/prices/cheap`, cached data, header-token auth), and
`AmadeusFareProvider` (retained for reference after the Self-Service shutdown). A
factory resolves `FARE_PROVIDER`; the thin `GET /api/v1/offers/cheapest` endpoint
validates input and maps `None`→404 / `ProviderError`→502.

## Technical Context

**Language/Version**: Python 3.13 (prod container `python:3.13-slim`, `Dockerfile:2`)

**Primary Dependencies**: FastAPI + Pydantic v2 (`requirements.txt:6,9`), httpx for
outbound provider calls (`requirements.txt:8`)

**Storage**: none in this capability — offers are transient; persistence is spec 002/003

**Testing**: Bruno contract suite `bruno/cheapsawari/offers/` (7 requests) against the
mock on dev port 8050 (`bruno/cheapsawari/environments/local.bru`)

**Target Platform**: same FastAPI service everywhere — local uvicorn (port 8050) and
Cloud Run `cheapsawari-api` (spec 007)

**Project Type**: web service (single backend, provider plug-ins)

**Performance Goals**: single upstream HTTP call per lookup, bounded by
`REQUEST_TIMEOUT_S` (15 s default, `src/config.py:57`)

**Constraints**: $0/mo — mock is free; Travelpayouts is free (affiliate-token gated, no
per-call charge); token must never appear in URLs/logs (header auth,
`src/providers/travelpayouts.py:22-23,65`)

**Scale/Scope**: 3 provider implementations + 1 factory + 1 endpoint (~370 lines)

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** Every provider file is mapped with a
  functional description (`Project_Structure.md:31-35`) and both the Slice 1 and the
  migration changelog rows list the exact files touched (rows 2026-06-21, 2026-06-24).
- **II. Pattern Reference Integrity — PASS.** The seam IS the pattern: "new fare
  sources go behind `FareProvider`… Amadeus is dead"
  (`.specify/memory/constitution.md:29`); the migration extended the seam instead of
  bypassing it.
- **III. Automated Maintenance via Agentic Skills — PASS.** `scripts/verify_structure.py`
  enforces that the provider files stay logged; no capability-specific script needed.
- **IV. Continuous API Validation (Bruno) — PASS.** `bruno/cheapsawari/offers/` (7
  requests / 24 assertions at Slice 1) covers the endpoint's happy path and all three
  failure codes; still green inside the current 97/242 full gate.
- **V. Infrastructure-as-Code & Cost Gating — PASS.** No infra of its own ($0: mock
  local, Travelpayouts free); the Slice 1 cost review recorded $0 and the migration
  kept it (changelog rows). Terraform correctly untouched by this capability.

## Project Structure

### Documentation (this feature)

```text
specs/001-fare-provider-seam/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    ├── fare-provider-contract.md
    └── openapi-offers.yaml
```

### Source Code (repository root)

```text
src/
├── models.py                 # Offer (normalized fare record)          (Slice 1)
├── config.py                 # FARE_PROVIDER + provider settings       (Slice 1; TP keys 2026-06-24)
├── main.py                   # GET /health, GET /api/v1/offers/cheapest (Slice 1; auth gate Slice 6)
└── providers/
    ├── base.py               # FareProvider ABC + ProviderError        (Slice 1)
    ├── mock.py               # deterministic default provider          (Slice 1)
    ├── amadeus.py            # DEPRECATED reference implementation     (Slice 1; superseded 2026-06-24)
    ├── travelpayouts.py      # live provider (Aviasales cached fares)  (2026-06-24)
    └── factory.py            # FARE_PROVIDER resolution                (Slice 1; TP branch 2026-06-24)
```

**Structure Decision**: one package per seam (`providers/`) with a `base.py` contract +
`factory.py` selector — the template every later seam (store, users, alerts) copied.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dead `amadeus.py` kept in-tree | Preserves the OAuth2/quota-budget reference implementation and keeps the factory's error message honest about known names | Deleting it was rejected: zero runtime cost (only imported by the factory), and it documents the quota math that shaped `POLL_MAX_PER_RUN` |
