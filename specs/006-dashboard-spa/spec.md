# Feature Specification: Dashboard SPA — Cards, Details/Edit, Themes, Booking Links

**Feature Branch**: `retro/006-dashboard-spa` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 5, 2026-06-23; Slice 15 UI, Slice 16c/d, 2026-06-25;
Slices 17–20, 2026-06-26)

**Input**: retro-spec conversion of the dashboard UI arc: Slice 5 (minimal dashboard),
15 (Details modal + Edit + hidden-fields fixes), 16 (5 themes, per-card Refresh,
Reload rename, alert-threshold field), 17 (date-picker UX), 18 (airline + Aviasales
link + sticky header), 19 (manual "Log a price" form), 20 (three booking links).

## Why

The tracker needed a face without becoming a second deployable: one self-contained
HTML file (vanilla JS + inline SVG, no build step, no CDN, no framework) served by the
same FastAPI app at `GET /` — so the whole product stays one $0 Cloud Run service. The
later slices are all owner-driven UX: see every configured leg before data exists,
edit without losing history, themes, genuinely fetch a fare on demand, dates that
can't be wrong, and — reflecting the product goal (personal invite-only tool, NOT an
OTA) — three labelled booking paths per fare including book-direct-with-the-airline.

## User Scenarios & Testing

### User Story 1 - See all trackings at a glance (Priority: P1)

A signed-in user sees a card per watch: route headline (→ / ⇄ / multi-city chain),
latest total, per-leg breakdown, a price sparkline, snapshot count, and the signature
"▼ Bucket reopened −X%" badge.

**Why this priority**: the product's read surface; Slice 5's reason to exist.

**Independent Test**: `bruno/cheapsawari/dashboard/get_dashboard.bru` (route returns
HTML); visual flows verified with Playwright per slice (changelog rows).

**Acceptance Scenarios**:

1. **Given** an unauthenticated visitor, **When** they hit `/`, **Then** 302 to
   `/login` — the landing page never leaks tracked routes (`src/main.py:84-94`).
2. **Given** watches exist, **When** the page loads, **Then** it fetches
   `/api/v1/watches` then per-watch snapshots+signal in parallel and renders cards
   (`src/web/dashboard.html:449-475`), any 401 redirecting to `/login` (:333-338).
3. **Given** ≥2 snapshots, **Then** an inline-SVG sparkline renders, green when the
   latest price is below the first (:350-365); badges: reopened / watching / no data
   yet (:367-374).
4. **Given** a multi-city watch, **Then** the headline is the full chain
   (A → B → C…) with a legs-count tag (:380-391).

---

### User Story 2 - Add / edit / delete a tracking from the form (Priority: P1)

One form covers one-way / round-trip / multi-city (dynamic leg-builder rows), the
per-watch alert threshold, and doubles as the edit form (pre-filled, submits PUT).

**Why this priority**: the write surface; edit reuse (Slice 15) closed the owner's
"fix my trip" ask.

**Independent Test**: Playwright (Slice 15): Details shows all 6 legs, Edit pre-fills,
one-way hides Return, round-trip reveals it, UI edit issues PUT, zero console errors.

**Acceptance Scenarios**:

1. **Given** trip-type switching, **Then** `.simple`/`.rt`/multi-city builder sections
   show/hide and `required` flags track visibility (hidden required fields would block
   submit) (:535-548); `[hidden]{display:none!important}` guarantees the UA rule wins
   over flex layout (:49-54 — the Slice 15 one-way fix).
2. **Given** multi-city, **Then** leg rows can be added/removed (≥2 enforced client
   side, :552-557) and submit builds a `legs[]` body (:570-581).
3. **Given** Edit, **Then** the form pre-fills from state, banner + "Save changes"
   appear, and submit branches to `PUT /api/v1/watches/{id}` (:597-601,634-645);
   Cancel restores add mode (:648-656).
4. **Given** the Alert −% field, **Then** blank means server default; a value posts
   `alert_threshold_pct` (:566-568,596).

---

### User Story 3 - Live per-card Refresh + manual price log (Priority: P2)

"↻ Refresh" on a card fetches a real fare NOW (`POST .../refresh`); the Details modal's
"Log a price (manual)" records a hand-observed price (backfill allowed).

**Why this priority**: closes the gap between the daily poll and "what is it right
now"; manual logging answers "how do I set a baseline" (Slice 19).

**Independent Test**: Playwright (Slice 19): logging 900/900/900/365 → 4 snapshots,
card shows 365.00 + "▼ Bucket reopened −59.44%"; (Slice 16) per-card Refresh records a
snapshot.

**Acceptance Scenarios**:

1. **Given** Refresh succeeds with data, **Then** the page reloads and shows "✓ Latest
   fare fetched: …"; with no cached fare, an honest explanation of Travelpayouts cache
   sparsity is shown AFTER the reload (ordering fix noted in code, :799-812).
2. **Given** the header, **Then** the old global "Refresh" is renamed **Reload**
   (re-pull + re-render only, :179) — distinct from the per-card live fetch (:441).
3. **Given** a manual price + optional past date, **Then**
   `POST .../snapshots {price, observed_at}` (noon UTC to keep the calendar date
   stable) and the modal re-renders with the new history (:733-761); the hint states
   email alerts still come from the daily poll (:719-721).

---

### User Story 4 - Date pickers that can't be wrong (Priority: P2)

Clicking anywhere on a date field opens the calendar; no past dates; return ≥
departure; each multi-city leg ≥ the previous leg.

**Why this priority**: two explicit owner asks (Slice 17).

**Independent Test**: Playwright (Slice 17): departure min=today; click fires
showPicker; too-early return auto-bumps; leg N min follows leg N−1; zero console
errors.

**Acceptance Scenarios**:

1. **Given** any `input[type=date]` click, **Then** a delegated handler calls
   `showPicker()` (guarded for old browsers / non-gesture) — works for dynamically
   added leg rows too (:500-508).
2. **Given** floors, **Then** `syncSimpleDateFloors`/`syncLegDateFloors` re-apply on
   trip-type switch, departure change, leg changes, add/remove leg, edit-prefill, and
   initial load (:510-561,630-631,835); editing a watch with already-past dates keeps
   them valid (floor relaxes to the existing value, :514-517,527).

---

### User Story 5 - Airline names, themes, and three booking links (Priority: P3)

Each priced leg shows its airline; the user books via Aviasales (accurate match),
Google Flights (neutral compare), or the airline's own site (book direct); five color
themes persist across visits.

**Why this priority**: the "not an OTA" product stance (Slice 20) + owner UX polish
(16/18).

**Independent Test**: Playwright (Slices 18/20): one-way link `JFK1507LAX1`,
round-trip `DTW1008AMS20081`, marker appended, all three links with correct hrefs on
card and Details, legend present; (16) 5 themes apply + persist.

**Acceptance Scenarios**:

1. **Given** a carrier code, **Then** a 38-entry IATA→name map renders the airline
   (fallback to code) (:249-259).
2. **Given** a priced leg, **Then** `bookLinks()` renders Aviasales (route+date
   encoded DDMM, affiliate `marker` appended when `/health` exposes one), Google
   Flights (natural-language query), and the airline's official site from a 38-carrier
   map — each with an explanatory tooltip; a visible legend explains the trio in
   Details (:263-317,712); round-trip watches get one round-trip search on the
   outbound leg (:397-411,669-680).
3. **Given** the theme button, **Then** it cycles midnight/nord/forest/daylight/sepia
   via `data-theme` on `<html>`, persisted in localStorage with a no-flash head script;
   `color-scheme` per theme keeps the native date picker legible (:7-10,12-47,766-779).
4. **Given** scrolling, **Then** the header stays visible (`position: sticky`,
   :62-67).

### Edge Cases

- **Details before any snapshot**: the modal's leg table derives from the watch itself
  via `watchLegs()` — a frontend mirror of `resolved_legs` — so a 6-leg chain is
  visible with "—" prices (the exact gap the owner hit) (:319-331,661-711).
- **Airline unknown to the site map**: only Aviasales + Google Flights render
  (:306-308).
- **`/health` unreachable**: provider label / marker fetch fails silently; cards still
  load (:453).
- **Delete while editing**: deleting the watch being edited cancels edit mode
  (:827-832).
- **Non-goal**: no client-side state framework, router, or build pipeline — one file,
  by design.

## Requirements

### Functional Requirements

- **FR-001**: The dashboard MUST be a single self-contained HTML file served by the
  same app at `GET /`, auth-gated by redirect (`src/main.py:76-94`;
  `src/web/dashboard.html`).
- **FR-002**: All data access MUST go through the existing JSON API from the same
  origin (fetch; 401 → `/login`) — no dashboard-only endpoints
  (`dashboard.html:239,333-338`; Slice 19 explicitly reused `POST .../snapshots`).
- **FR-003**: The edit flow MUST reuse the add form (pre-fill + PUT), preserving the
  backend's identity/history guarantees (spec 002 FR-006).
- **FR-004**: Booking links MUST be labelled with their trade-offs (accurate /
  may-change / re-enter-details) because no provider gives a bookable fare token —
  every link is a search (Slice 20 changelog; `dashboard.html:296-317`).
- **FR-005**: The affiliate `marker` MUST come from `GET /health` (public, optional,
  null-safe) — `TRAVELPAYOUTS_MARKER` config exposed at `src/main.py:112-120`,
  consumed at `dashboard.html:246,263-269`.
- **FR-006**: Themes MUST apply before first paint (no flash) and persist client-side
  only (`dashboard.html:7-10,766-779`).

### Key Entities

- **state.byId**: client cache `{watch, snaps, signal}` per watch id powering
  Details/Edit without re-fetching (`dashboard.html:243-246,468-469`).
- **AIRLINES / AIRLINE_SITES**: 38-carrier IATA→name and IATA→official-site maps
  (`dashboard.html:249-258,280-294`).

## Success Criteria

- **SC-001**: Bruno gate unchanged across UI slices (97 req / 242 assert / 13 tests) —
  frontend-only changes verified instead by headless Playwright with zero console
  errors (changelog rows Slices 15–20).
- **SC-002**: One deployable: the dashboard added no hosting, build step, dependency,
  or cost (Slice 5 changelog; `src/main.py:76-78`).
- **SC-003**: Slice 20's booking trio verified live: correct Aviasales/Google/airline
  hrefs on card and Details, legend present (Playwright, changelog 2026-06-26).

## Assumptions

- Modern evergreen browser (showPicker guarded for older ones; localStorage
  try/caught).
- Aviasales' DDMM search-path encoding and Google Flights' natural-language query
  remain stable (client-side constructed URLs, no API).
- The affiliate marker is optional and currently null in prod — no attribution, by
  owner's choice (memory/product note; `/health` returns `marker: null` until set).
