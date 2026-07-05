# Feature Specification: Watch Tracking — CRUD, Round-Trip, Multi-City, Edit

**Feature Branch**: `retro/002-watch-tracking` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 2, 2026-06-22; Slice 7 round-trip+flex, Slice 9 multi-city,
2026-06-24; Slice 15 edit-in-place, 2026-06-25)

**Input**: retro-spec conversion of Slices 2, 7, 9, 15 (backend) — the "watch" entity:
register a trip, persist it, price it as a trip, edit it in place.

## Why

A fare tracker is only useful if a trip can be *registered once and watched forever*.
Slice 2 created the durable `Watch` entity behind a `WatchRepository` seam (SQLite dev /
Firestore prod). Real trips aren't single one-way hops, so Slice 7 added round trips
with a flexible date window per leg, and Slice 9 generalized to N-leg multi-city chains —
which also delivered the owner's transfer-airport and port-of-entry asks with zero extra
code (route a leg through a hub: DTW→CDG→AMD). Slice 15 closed "I mis-typed my trip":
edit the definition in place without losing the accumulated price history.

## User Scenarios & Testing

### User Story 1 - Track a one-way route (Priority: P1)

A user registers origin/destination/date and can list, fetch, refresh (record a price)
and delete the watch; deleting removes its history.

**Why this priority**: the core entity — every other capability (poll, signal, alerts,
dashboard) hangs off a watch.

**Independent Test**: `bruno/cheapsawari/watches/` (10 requests): create → get → list →
refresh ×2 → snapshots → delete → verify 404.

**Acceptance Scenarios**:

1. **Given** a valid body, **When** `POST /api/v1/watches`, **Then** 201 with a uuid4
   `id`, `active=true`, UTC `created_at`, server-stamped `owner_email`
   (`src/main.py:282-296`; `src/store/sqlite_store.py:157-173`).
2. **Given** `origin == destination` on a non-multi-city trip, **When** created or
   edited, **Then** 400 (`src/main.py:290-291,330-331`).
3. **Given** an existing watch, **When** `POST .../refresh`, **Then** the active
   provider prices the trip and a snapshot is stored; `recorded=false` (200) when no
   inventory; 502 on ProviderError (`src/main.py:353-379`).
4. **Given** a watch is deleted, **When** its snapshots are looked up, **Then** they are
   gone too (SQLite FK cascade `src/store/sqlite_store.py:58`; explicit subcollection
   delete on Firestore `src/store/firestore_store.py:191-193`).

---

### User Story 2 - Round trip with flexible dates (Priority: P2)

A user tracks DTW⇄AMS where each leg may float up to N days past its anchor date; the
tracked price is the cheapest outbound + cheapest return.

**Why this priority**: most real trips are round trips; flexibility is where the
savings live.

**Independent Test**: `bruno/cheapsawari/roundtrip/` (9 requests) asserts trip-total =
outbound+return and chosen dates fall inside the flex windows.

**Acceptance Scenarios**:

1. **Given** `trip_type=round_trip` without `return_date`, **When** created, **Then**
   422 (`src/models.py:139-143`).
2. **Given** `return_date < departure_date`, **When** created, **Then** 422
   (`src/models.py:142-143`).
3. **Given** `flex_days=N` on a leg, **When** priced, **Then** N+1 consecutive dates
   are searched and the cheapest kept (`src/trip.py:40-61`); flex capped at
   `MAX_FLEX_DAYS=21` (`src/models.py:21,97-102`).
4. **Given** a priced round trip, **Then** the snapshot carries
   `outbound_price/outbound_date/return_price/return_date` plus the total
   (`src/store/base.py:36-55`).

---

### User Story 3 - Multi-city chains (transfer hub / port of entry) (Priority: P2)

A user tracks an explicit chain of 2–6 legs — including "same start and end city"
round-shaped chains — and each leg keeps its own date + flexibility.

**Why this priority**: delivers the owner's transfer-airport and port-of-entry choice
on the existing route-level $0 data (Slice 9 changelog).

**Independent Test**: `bruno/cheapsawari/multicity/` (6 requests): 4-leg create+refresh,
total=Σ legs, per-leg persistence, <2-legs and same-city-leg 422 guards.

**Acceptance Scenarios**:

1. **Given** `trip_type=multi_city` with fewer than 2 legs (or > `MAX_LEGS=6`),
   **When** created, **Then** 422 (`src/models.py:119-123`).
2. **Given** a legs chain, **Then** overall origin/destination/departure_date are
   derived from first/last leg — the client may omit them (`src/models.py:124-127`);
   an overall same-city chain is legal while per-leg origin≠destination is enforced
   (`src/models.py:38-44`; `src/main.py:287-291`).
3. **Given** any trip shape, **When** priced, **Then** it resolves through the single
   `Watch.resolved_legs` path — one-way=1, round-trip=2, multi-city=N
   (`src/models.py:149-163`; `src/trip.py:64-80`).

---

### User Story 4 - Edit a tracking in place (Priority: P3)

A user changes route/dates/flex/cabin/trip-type/legs of an existing watch; identity,
lifecycle and price history are preserved.

**Why this priority**: quality-of-life; delete+recreate was the workaround but lost
history.

**Independent Test**: `bruno/cheapsawari/update/` (6 requests): create → edit to
round-trip → GET persisted → same-city 400 → edit to multi-city → cleanup.

**Acceptance Scenarios**:

1. **Given** an owned watch, **When** `PUT /api/v1/watches/{id}` with a valid
   `WatchCreate` body, **Then** the trip definition is replaced while `id`,
   `created_at`, `owner_email`, `active` and all snapshots are preserved
   (`src/main.py:318-338`; `src/store/base.py:73-85`; sqlite
   `src/store/sqlite_store.py:204-245`; firestore `src/store/firestore_store.py:138-175`).
2. **Given** a shape change (e.g. multi-city → round-trip), **Then** stale fields are
   normalized by the same model validator as create (legs nulled for flat shapes,
   `src/models.py:138`; return fields nulled for one-way, `src/models.py:144-146`).

### Edge Cases

- **Pre-existing local DBs**: SQLite migrations diff `PRAGMA table_info` and `ALTER
  TABLE` missing columns (Slices 7/8/9/16 columns), so old files upgrade in place
  (`src/store/sqlite_store.py:63-83,98-104`).
- **Legacy rows**: pre-Slice-7 rows read with defaults (`trip_type='one_way'`, flex 0);
  Firestore reads are schemaless-tolerant (`src/store/firestore_store.py:59-74`).
- **Unknown watch id**: store raises `WatchNotFoundError` for snapshot ops
  (`src/store/base.py:10,116-117`); the API returns 404 via the ownership helper
  (spec 005).
- **Non-goal**: pausing (`active=false`) is modeled and respected by the poll
  (`src/poll.py:72`) but no endpoint flips it — there is no pause/resume API.

## Requirements

### Functional Requirements

- **FR-001**: Watches MUST be persisted behind `WatchRepository` with `create_watch`,
  `get_watch`, `update_watch`, `list_watches(active_only, owner_email)`,
  `delete_watch`, `add_snapshot`, `list_snapshots` (`src/store/base.py:58-125`).
- **FR-002**: The store backend MUST be selected by `WATCH_STORE` (`sqlite` default |
  `firestore` prod), with the Firestore client imported lazily
  (`src/store/factory.py:15-30`).
- **FR-003**: `WatchCreate` MUST validate trip shape at the model layer: legal
  `trip_type` ∈ {one_way, round_trip, multi_city} (`src/models.py:17,116-117`),
  round-trip date ordering, multi-city leg count 2..6, per-leg origin≠destination,
  flex 0..21.
- **FR-004**: Every trip shape MUST price through one code path:
  `price_watch_trip(provider, watch)` sums per-leg cheapest offers over each leg's flex
  window; any leg with no inventory → no quote (`src/trip.py:64-80`).
- **FR-005**: Watch routes MUST be exposed as `POST/GET/PUT/DELETE /api/v1/watches[/{id}]`
  plus `POST .../refresh` and `GET .../snapshots`, all session-gated and
  ownership-scoped (`src/main.py:282-395`; ownership in spec 005).
- **FR-006**: `update_watch` MUST preserve identity/lifecycle/owner and keep the
  snapshot series (`src/store/base.py:73-85`).
- **FR-007**: Watch mutations MUST emit structured events `watch.create`,
  `watch.update`, `watch.delete` (`src/main.py:293-295,335-337,350`).

### Key Entities

- **Watch / WatchCreate / TripLeg**: the tracked trip (full shapes in data-model.md).
- **TripQuote**: transient priced trip — one `Offer` per leg + total (`src/trip.py:29-37`).
- **PriceSnapshot / SnapshotLeg**: persisted observation (owned jointly with spec 003).

## Success Criteria

- **SC-001**: Bruno suites `watches/` (10), `roundtrip/` (9), `multicity/` (6),
  `update/` (6) — all green inside the full 97 req / 242 assert / 13 test gate
  (changelog rows Slices 2/7/9/15).
- **SC-002**: Slice 7/9 shipped backward-compatible: pre-existing one-way watches kept
  working with defaulted columns (changelog 2026-06-24; migration code
  `src/store/sqlite_store.py:63-83`).
- **SC-003**: Slice 15 verified in-process (created_at preserved, return_date cleared
  on shape change, 404 on unknown) and via headless Playwright on the UI edit flow
  (changelog 2026-06-25).

## Assumptions

- Personal scale (a handful of watches per user): per-operation SQLite connections and
  Python-side Firestore filtering are deliberate simplicity choices
  (`src/store/sqlite_store.py:4-5`; `src/store/firestore_store.py:12-14,179`).
- `MAX_FLEX_DAYS=21` and `MAX_LEGS=6` bound provider fan-out per poll
  (`src/models.py:18-23`) — quota math documented in spec 003.
- Ownership enforcement is an API-layer concern (`_owned_watch`, spec 005); stores are
  ownership-agnostic beyond the `owner_email` field/filter.
