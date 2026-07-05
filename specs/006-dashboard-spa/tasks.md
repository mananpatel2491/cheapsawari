---
description: "As-built task record for the dashboard SPA (Slices 5, 15–20)"
---

# Tasks: Dashboard SPA

As-built record — reconstructed 2026-07-05 from Slices 5 (2026-06-23), 15/16
(2026-06-25), 17/18/19/20 (2026-06-26). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Minimal dashboard (US1, US2)

- [X] T001 [US1] `src/web/dashboard.html`: cards with route/meta/price, inline-SVG
  sparkline, reopened/watching/no-data badges, parallel snapshot+signal fetch
  (Slice 5)
- [X] T002 [US2] Add-watch form + delete action calling the JSON API same-origin;
  served at `GET /` via FileResponse (Slice 5)
- [X] T003 [US1] Auth integration: 401 → `/login` redirect, user bar, sign-out, Admin
  link for the owner (Slice 6)
- [X] T004 Form growth: trip-type switching + flex fields (Slice 7); multi-city
  leg-builder + transfer/PoE hint (Slice 9)

## Phase 2: Details + Edit (US2)

- [X] T005 [US2] Details modal — kv sheet + leg table derived from `watchLegs()`
  (resolved_legs mirror) so all legs show pre-data (Slice 15)
- [X] T006 [US2] Edit mode — pre-filled form, banner + Cancel, PUT branch (Slice 15)
- [X] T007 [US2] CSS fixes: `[hidden]{display:none!important}` (one-way hides Return),
  `color-scheme` for the date-picker icon/popup (Slice 15; invert hack retired
  Slice 16)

## Phase 3: Themes, thresholds, live refresh (US3, US5)

- [X] T008 [US5] 5-skin theme system (`data-theme`, localStorage, no-flash head
  script, per-theme `color-scheme`) + cycle button (Slice 16)
- [X] T009 [US2] Alert −% field posting `alert_threshold_pct`; shown in Details
  ("custom" vs "default (−15%)") (Slice 16)
- [X] T010 [US3] Per-card genuine ↻ Refresh (`POST .../refresh`) with honest
  no-cached-fare messaging; header action renamed Reload (Slice 16)

## Phase 4: Date UX (US4)

- [X] T011 [US4] Click-anywhere `showPicker()` delegation (guarded) incl. dynamic leg
  rows (Slice 17)
- [X] T012 [US4] Date floors: no past, return ≥ departure, leg N ≥ leg N−1; re-applied
  on every relevant event; edit keeps past dates valid (Slice 17)

## Phase 5: Airlines + booking (US5)

- [X] T013 [US5] Airline display per leg (38-entry IATA→name map) + Aviasales deep
  link with optional affiliate `marker` from `/health`; `TRAVELPAYOUTS_MARKER` setting;
  sticky header (Slice 18)
- [X] T014 [US3] Manual "Log a price" form in Details (existing snapshots endpoint;
  past dates for backfill; baseline-clarifying hint) (Slice 19)
- [X] T015 [US5] Three booking links per fare (Aviasales / Google Flights /
  airline-direct via 38-carrier AIRLINE_SITES map) + tooltips + visible legend
  (Slice 20)
- [X] T016 Playwright verification per slice, zero console errors (Slices 15–20
  changelog rows)

## Open follow-ups (genuinely pending)

- [ ] T017 Prod affiliate marker is unset (`marker: null`) — no attribution; owner may
  set `TRAVELPAYOUTS_MARKER` on Cloud Run whenever desired (links already handle it)
- [ ] T018 AIRLINES/AIRLINE_SITES maps cover 38 carriers — unmapped carriers show the
  raw code and lose the book-direct link; extend as they appear in real data
