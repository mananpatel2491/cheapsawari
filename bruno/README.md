# API Validation (bruno/)

This directory contains Bruno collections for continuous API validation and contract testing.

## Rules
1. No backend API feature is complete until the Bruno pipeline is updated and passing.
2. Successful Bruno execution is required for all commits (AVF Contract-First Validation gate).

## Structure
- `cheapsawari/` — the API collection (collection root holds `bruno.json`).
  - `environments/local.bru` — `baseUrl` for the local dev server.
  - `offers/` — requests for the fare-fetch seam (`/health`, `/api/v1/offers/cheapest`).

## Running the gate
The suite runs against the **mock** provider, so it never spends the Amadeus quota.

```bash
# 1. Start the API on the cheapsawari dev port (8050), mock provider:
FARE_PROVIDER=mock python -m uvicorn src.main:app --port 8050

# 2. In another shell, run the collection:
cd bruno/cheapsawari && bru run offers --env local
```

## Current status
`offers/` — **7 requests / 24 assertions, all passing** (Slice 1).
Covers: liveness + active provider, the deterministic Offer contract, lower-case IATA
normalization, cabin pass-through, and the 404 / 400 / 422 error envelope.
