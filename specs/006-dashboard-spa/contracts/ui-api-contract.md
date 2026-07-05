# UI↔API Contract: what the dashboard consumes

The SPA has NO endpoints of its own — it composes the JSON API same-origin. This table
is the frontend's dependency surface (see also `Function_Mapping.md`, the repo's
standing traceability map).

| UI element | Call | Source (dashboard.html) |
|---|---|---|
| page gate | `GET /` → 302 `/login` when signed out (server-side) | src/main.py:84-94 |
| header provider + marker | `GET /health` → `{provider, marker}` | :453, :246 |
| user bar / Admin link | `GET /api/v1/auth/me` | :341-347 |
| Sign out | `POST /api/v1/auth/logout` | :781-784 |
| cards | `GET /api/v1/watches` + per watch `GET .../snapshots?limit=100` + `GET .../signal` (parallel) | :449-470 |
| + Track | `POST /api/v1/watches` (one_way/round_trip body or multi_city legs[]; optional `alert_threshold_pct`) | :563-612 |
| Save changes (edit) | `PUT /api/v1/watches/{id}` (same body shape) | :597-601 |
| Delete | `DELETE /api/v1/watches/{id}` (confirm dialog) | :827-832 |
| per-card ↻ Refresh | `POST /api/v1/watches/{id}/refresh` → RefreshResult | :786-823 |
| Log a price (Details) | `POST /api/v1/watches/{id}/snapshots` `{price[, observed_at=<date>T12:00:00Z]}` | :733-761 |
| any 401 | client redirects to `/login` | :333-338 |

## Client-side conventions the API relies on / provides

- **Ownership is invisible to the UI**: the list is already scoped server-side; a
  foreign id would 404 (spec 005).
- **Snapshots arrive newest-first**; the sparkline reverses to chronological
  (:424-427).
- **`RefreshResult.recorded=false`** is a normal outcome (sparse Travelpayouts cache)
  and gets the explanatory message, not an error style (:806-812).
- **Legs alignment**: the latest snapshot's `legs[i]` lines up with configured leg i
  in the Details table (:667-668) — guaranteed by `build_snapshot` preserving leg
  order (`src/store/base.py:29-35`).

## Outbound (third-party) links — constructed, not called

| Link | Base | Notes |
|---|---|---|
| Aviasales | `https://www.aviasales.com/search/` + `{O}{DDMM}{D}[{DDMM}]1` | `?marker=` appended when `/health.marker` non-null |
| Google Flights | `https://www.google.com/travel/flights?q=…` | natural-language query |
| Airline direct | `AIRLINE_SITES[carrier]` (38 carriers) | homepage/booking entry; user re-enters details |
