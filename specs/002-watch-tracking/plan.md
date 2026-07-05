# Implementation Plan: Watch Tracking — CRUD, Round-Trip, Multi-City, Edit

**Branch**: `retro/002-watch-tracking` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slice 2 (2026-06-22), Slices 7+9 (2026-06-24),
Slice 15 backend (2026-06-25).

## Summary

`WatchRepository` (`src/store/base.py`) is the persistence seam with two
implementations: `SqliteWatchRepository` (stdlib, per-op connections, FK cascade,
pragma-diff migrations) and `FirestoreWatchRepository` (`watches/{id}` +
`snapshots/` subcollection, explicit cascade). `WatchCreate`'s model validator owns all
trip-shape rules; `Watch.resolved_legs` normalizes every shape to an ordered leg list
that `src/trip.py:price_watch_trip` prices via the spec-001 provider seam (flex-window
search per leg, summed). FastAPI routes in `src/main.py:282-395` expose CRUD + refresh +
snapshots, and `update_watch` performs the history-preserving in-place edit.

## Technical Context

**Language/Version**: Python 3.13, FastAPI + Pydantic v2 (model validators)

**Primary Dependencies**: stdlib `sqlite3`+`json` (default store),
`google-cloud-firestore` (prod store, `requirements.txt:12`)

**Storage**: SQLite file `cheapsawari.db` (`SQLITE_PATH`, `src/config.py:59`) or Cloud
Firestore `watches/{id}` + `snapshots` subcollection (`src/store/firestore_store.py:4-8`)

**Testing**: Bruno `watches/`, `roundtrip/`, `multicity/`, `update/` suites (31 request
files) on port 8050; in-process TestClient checks recorded in changelog rows

**Target Platform**: same single service, local + Cloud Run

**Project Type**: web service (entity + repository layer)

**Performance Goals**: pricing fan-out bounded by Σ(flex_days+1) per leg, ≤ 6 legs ×
22 dates worst case

**Constraints**: $0/mo (Firestore free tier; no composite indexes by design —
Python-side filtering at personal scale)

**Scale/Scope**: 2 stores (~550 lines), 1 trip-pricing module, ~115 lines of routes

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** All store/trip files mapped
  (`Project_Structure.md:36-39,46`); each contributing slice logged its exact file list
  in the changelog (rows 2026-06-22, 2026-06-24 ×2, 2026-06-25).
- **II. Pattern Reference Integrity — PASS.** "persistence behind `WatchRepository`
  (SQLite dev / Firestore prod)" is a named sacred seam
  (`.specify/memory/constitution.md:29`); Slices 7/9/15 extended the seam signatures
  rather than bypassing them (`build_snapshot` shared helper, `src/store/base.py:14-55`).
- **III. Automated Maintenance via Agentic Skills — PASS.** verify_structure gate green
  on every slice commit; migrations are code, not manual steps.
- **IV. Continuous API Validation (Bruno) — PASS.** Four dedicated suites (`watches/`
  10, `roundtrip/` 9, `multicity/` 6, `update/` 6 request files); gate counts grew
  17/52 → 64/167 → 84/199 → 90/224 across the slices (changelog rows) and sit inside
  today's 97/242/13.
- **V. Infrastructure-as-Code & Cost Gating — PASS.** No new infra: SQLite is local;
  Firestore was provisioned in Slice 3b and codified in terraform (spec 007). Each
  slice's cost review recorded $0 (changelog rows; flex fan-out bounded by
  MAX_FLEX_DAYS/MAX_LEGS to keep polling free).

## Project Structure

### Documentation (this feature)

```text
specs/002-watch-tracking/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    ├── openapi-watches.yaml
    └── storage-contract.md
```

### Source Code (repository root)

```text
src/
├── models.py                 # TripLeg/WatchCreate/Watch/SnapshotLeg/PriceSnapshot  (S2; S7/S9 shapes; S16 threshold field)
├── trip.py                   # price_watch_trip + TripQuote + flex-window search   (S7; multi-city S9)
├── main.py:268-395           # watch routes (POST/GET/PUT/DELETE/refresh/snapshots) (S2; PUT S15)
└── store/
    ├── base.py               # WatchRepository ABC + build_snapshot + WatchNotFoundError (S2; legs S9; update S15)
    ├── sqlite_store.py       # default store, schema + pragma-diff migrations      (S2; columns S7/S8/S9/S16)
    ├── firestore_store.py    # prod store, explicit snapshot cascade               (S3b; fields S7/S8/S9/S16)
    └── factory.py            # WATCH_STORE resolution, lazy firestore import       (S2/S3b)
```

**Structure Decision**: repository pattern mirroring `providers/` — contract + two
stores + factory; trip pricing is a pure module composing the provider seam so both
stores and both providers share one pricing path.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Snapshot keeps both `legs[]` (canonical) and `outbound_*/return_*` (convenience) | Slice 7 shipped the flat fields; Slice 9 added the general list without breaking Bruno assertions or old rows | Dropping the flat fields was rejected — backward compatibility with existing snapshots and simpler dashboard access for the two common shapes |
| Python-side filtering/sorting in the Firestore store | avoids composite-index management for `active+created_at` queries | index-backed queries rejected at personal scale (few watches; $0 posture, `firestore_store.py:12-14`) |
