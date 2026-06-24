# API Validation (bruno/)

This directory contains Bruno collections for continuous API validation and contract testing.

## Rules
1. No backend API feature is complete until the Bruno pipeline is updated and passing.
2. Successful Bruno execution is required for all commits (AVF Contract-First Validation gate).

## Structure
- `cheapsawari/` — the API collection (collection root holds `bruno.json`).
  - `environments/local.bru` — `baseUrl` for the local dev server.
  - `offers/` — requests for the fare-fetch seam (`/health`, `/api/v1/offers/cheapest`).
  - `watches/` — requests for the watches+persistence seam (`/api/v1/watches` CRUD,
    `refresh`, `snapshots`). Self-contained: seq 1 creates a watch and captures its id,
    seq 9 deletes it, so the suite is idempotent and leaves no residue.
  - `poll/` — the quota-capped poll engine (`POST /api/v1/poll`): token guard (401),
    a run that records snapshots for active watches, and self-cleanup. Needs the server
    started with `POLL_TOKEN` matching `pollToken` in `environments/local.bru`.
  - `auth/` (Slice 6) — the Google-auth gate + admin allowlist. Runs **first**
    (alphabetically) and seeds the session the rest of the collection relies on: a
    no-session 401, dev login as owner, allowlist add/list/revoke, owner-vs-invitee
    gating (403), and a non-allowlisted refusal. Needs the server started with
    `AUTH_MODE=dev` and `ADMIN_EMAIL` matching `adminEmail` in `environments/local.bru`.

## Running the gate
The suite runs against the **mock** provider, so it never spends the fare-API quota.
Since Slice 6 the API is auth-gated, so run the **whole collection in one pass** (not a
single folder): Bruno's per-run cookie jar carries the session the `auth/` folder
establishes to every protected folder.

```bash
# 1. Start the API on the cheapsawari dev port (8050): mock provider, dev auth, throwaway DB.
AUTH_MODE=dev ADMIN_EMAIL=mpatel.mi24@gmail.com SESSION_SECRET=test-secret \
  FARE_PROVIDER=mock SQLITE_PATH=.gate.db POLL_TOKEN=test-poll-token \
  python -m uvicorn src.main:app --port 8050

# 2. In another shell, run the full collection (auth/ runs first and seeds the session):
cd bruno/cheapsawari && bru run --env local
```

## Current status
**64 requests / 167 assertions / 5 tests, all passing.**
- `auth/` (Slice 6) — no-session 401, dev login (owner), allowlist add/list/revoke,
  owner-vs-invitee gating (403), non-allowlisted refusal, public auth-config.
- `roundtrip/` (Slice 7) — flexible round-trip create + refresh (trip total =
  outbound+return, both dates inside their flex windows), per-leg snapshot fields,
  one-way-with-flex, and the 422 guards (missing/invalid return_date).
- `offers/` (Slice 1) — liveness + active provider, the deterministic Offer contract,
  lower-case IATA normalization, cabin pass-through, and the 404 / 400 / 422 error envelope.
- `watches/` (Slice 2) — full watch lifecycle (create → get → list → refresh ×2 →
  snapshots → delete → confirm-deleted), plus 404 / 400 guards.
- `poll/` (Slice 3a) — token guard (401), quota-capped poll run records snapshots, cleanup.
- `signal/` (Slice 4) + `dashboard/` (Slice 5) — reopened-bucket detection and the SPA route.

> Note: individual protected folders (`bru run watches`) now 401 on their own — they need
> the session from `auth/`. Run the full collection, or prepend a dev login.
