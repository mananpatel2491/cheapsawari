---
description: "As-built task record for watch tracking (CRUD, round-trip, multi-city, edit)"
---

# Tasks: Watch Tracking

As-built record — reconstructed 2026-07-05 from Slices 2 (2026-06-22), 7/9 (2026-06-24),
15 (2026-06-25). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Persistence seam (US1)

- [X] T001 `src/store/base.py`: `WatchRepository` ABC + `WatchNotFoundError` (Slice 2)
- [X] T002 [US1] `src/store/sqlite_store.py`: schema, per-op connections, FK cascade,
  row↔model mapping (Slice 2)
- [X] T003 `src/store/factory.py`: `WATCH_STORE` resolution, lru_cache, lazy firestore
  import (Slice 2; firestore branch Slice 3b)
- [X] T004 [US1] Watch routes: POST/GET/DELETE `/api/v1/watches`, `POST .../refresh`,
  `GET .../snapshots` (Slice 2; ownership scoping Slice 8, spec 005)
- [X] T005 [US1] Bruno `watches/` suite (10 requests; gate 17 req / 52 assert at
  Slice 2)

## Phase 2: Round-trip + date flexibility (US2)

- [X] T006 [US2] `src/models.py`: `trip_type`/`return_date`/`depart_flex_days`/
  `return_flex_days` + model validator (round_trip ordering, MAX_FLEX_DAYS=21) (Slice 7)
- [X] T007 [US2] `src/trip.py`: `price_watch_trip` + `_cheapest_in_window` +
  `TripQuote`; snapshot price = trip total (Slice 7)
- [X] T008 [US2] `build_snapshot` shared helper + extended `add_snapshot` signature;
  sqlite ALTER-TABLE migrations; firestore back-compatible fields (Slice 7)
- [X] T009 [US2] Bruno `roundtrip/` suite (9 requests; gate 64/167/5) (Slice 7)

## Phase 3: Multi-city (US3)

- [X] T010 [US3] `TripLeg` model + `multi_city` trip type + `resolved_legs` + derived
  flat endpoints + 2..MAX_LEGS=6 validation (Slice 9)
- [X] T011 [US3] `SnapshotLeg` canonical per-leg breakdown (`legs_json` column /
  `legs` array) (Slice 9)
- [X] T012 [US3] Same-city-400 guard skipped for multi_city at create/update
  (`src/main.py:290,330`); per-leg origin≠destination enforced in the model (Slice 9)
- [X] T013 [US3] Bruno `multicity/` suite (6 requests; gate 84/199/12) (Slice 9)

## Phase 4: Edit in place (US4)

- [X] T014 [US4] `WatchRepository.update_watch` contract + sqlite UPDATE + firestore
  field update, preserving id/created_at/owner_email/active + history (Slice 15)
- [X] T015 [US4] `PUT /api/v1/watches/{id}` with create-parity validation +
  `watch.update` event (Slice 15)
- [X] T016 [US4] Bruno `update/` suite (6 requests; gate 90/224/13) (Slice 15)

## Open follow-ups (genuinely pending)

- [ ] T017 Pause/resume endpoint: `active` exists and the poll respects it, but no API
  flips it (`src/models.py:170`; `src/poll.py:72`)
- [ ] T018 Optional itinerary-level provider for true through-fares (roadmap "Next
  (planned)")
