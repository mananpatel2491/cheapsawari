# Data Model: Dashboard SPA

Nothing persisted server-side by this capability. Client-side state and the config it
consumes:

## Client state (`src/web/dashboard.html:243-246`)

| Field | Shape | Purpose |
|---|---|---|
| `state.byId` | `{ [watchId]: { w, snaps, signal } }` | populated by `load()` (:468-469); powers Details/Edit without re-fetching |
| `state.editingId` | `string \| null` | watch currently being edited; also relaxes date floors (:515-517,527) |
| `state.marker` | `string \| null` | affiliate marker from `/health` (:453); appended to Aviasales URLs (:267) |

## localStorage

| Key | Values | Notes |
|---|---|---|
| `cs_theme` | `midnight` (default) \| `nord` \| `forest` \| `daylight` \| `sepia` | read pre-paint by the head script (:7-10); written by `applyTheme` (:768-773) |

## Static lookup tables (client-side)

- `AIRLINES` — 38 IATA→display-name entries, fallback to the raw code (:249-259).
- `AIRLINE_SITES` — 38 IATA→official-site URLs for the book-direct link (:280-294).
- `THEMES` / `THEME_LABELS` — the five skins (:766-767).
- `BOOK_LEGEND` — the booking-links explainer shown in Details (:313-317).

## Constructed URLs (no API behind them)

| Builder | Shape | Example |
|---|---|---|
| `aviasalesUrl` (:263-269) | `https://www.aviasales.com/search/{O}{DDMM}{D}[{DDMM ret}]1[?marker=…]` | `JFK1507LAX1`, round-trip `DTW1008AMS20081` |
| `googleFlightsUrl` (:272-276) | `https://www.google.com/travel/flights?q=Flights from {O} to {D} on {date}[ returning {ret}]` | natural-language query |

## Server config consumed

| Key | Surface | Notes |
|---|---|---|
| `TRAVELPAYOUTS_MARKER` | `GET /health` → `marker` (`src/main.py:112-120`; `src/config.py:53-56,114`) | public affiliate id; optional — links work without it (prod: null) |
| provider name | `GET /health` → `provider` | shown in the header sub-line (:174,453) |
