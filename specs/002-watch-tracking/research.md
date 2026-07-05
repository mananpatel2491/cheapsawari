# Research: Watch Tracking — CRUD, Round-Trip, Multi-City, Edit

As-built record — decisions reconstructed 2026-07-05 from Slices 2/7/9/15 changelog rows
and module docstrings.

## Decision 1 — Repository seam with SQLite default, Firestore prod

**Choice**: `WatchRepository` ABC; stdlib SQLite as the zero-dependency hermetic
default, Firestore selected by `WATCH_STORE=firestore` (`src/store/base.py`;
`src/store/factory.py:15-30`).
**Why**: tests and local dev need durability without cloud credentials; prod needs to
survive Cloud Run's ephemeral filesystem. Lazy Firestore import keeps local runs free
of the GCP client (`factory.py:20-22`).
**Rejected**: in-memory store (loses history between restarts — the history IS the
product), Firestore-only (non-hermetic tests).

## Decision 2 — Model-validator-owned trip-shape rules

**Choice**: all shape validation lives in `WatchCreate._check_trip`
(`src/models.py:114-147`), and every shape normalizes through `resolved_legs`
(`src/models.py:149-163`).
**Why**: create and update (PUT reuses `WatchCreate`) get identical validation for
free; pricing, dashboard mirroring, and snapshot legs all consume one canonical leg
list.
**Rejected**: per-endpoint validation (drift between create and edit).

## Decision 3 — Flex window = compose the per-date seam, not a provider feature

**Choice**: a leg with `flex_days=N` is priced by N+1 single-date provider calls,
cheapest kept (`src/trip.py:40-61`).
**Why**: works identically on mock and Travelpayouts (neither offers a native
date-range search on the used endpoint); `ProviderError` propagates unmasked so a real
outage is never recorded as "no inventory" (`src/trip.py:51-53`).
**Cost bound**: `MAX_FLEX_DAYS=21` + `MAX_LEGS=6` cap the fan-out
(`src/models.py:18-23`) — free-tier math stays predictable.

## Decision 4 — Multi-city as the generalization, not a new feature

**Choice**: `multi_city` joins the existing `trip_type` enum; one-way/round-trip become
1- and 2-leg cases of the same leg-list pipeline (Slice 9; `src/models.py:15-17`).
**Why**: "transfer airport" and "port of entry" asks are just explicit legs
(DTW→CDG→AMD), so no itinerary-level provider was needed — $0 route-level data
suffices (Slice 9 changelog).
**Rejected**: an itinerary/through-fare provider (cost + not needed for trend
tracking; still the roadmap's only "next planned" item).

## Decision 5 — Idempotent in-place SQLite migrations

**Choice**: diff `PRAGMA table_info` against a `_MIGRATIONS` dict and `ALTER TABLE`
missing columns at store construction (`src/store/sqlite_store.py:63-83,98-104`).
**Why**: SQLite lacks `ADD COLUMN IF NOT EXISTS`; local DBs predating Slice 7 had to
upgrade silently; all added columns are nullable/defaulted so old rows stay valid.
**Rejected**: a migration tool (alembic) — overkill for one file-backed personal store.

## Decision 6 — Edit preserves history (Slice 15)

**Choice**: `update_watch` overwrites only trip-definition fields; `id`, `created_at`,
`owner_email`, `active`, and all snapshots survive (`src/store/base.py:73-85`).
**Why**: the accumulated series is the user's investment; "a caller wanting a clean
series should delete and re-create" is the documented escape hatch.
**Rejected**: PATCH-style partial updates (PUT-with-full-`WatchCreate` reuses the
validator wholesale; partial merge would need its own rules).
