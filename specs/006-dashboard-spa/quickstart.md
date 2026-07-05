# Quickstart: Dashboard SPA

## 1. Open it

Start the API (spec 001 quickstart step 0), then browse to
`http://127.0.0.1:8050/` → you are redirected to `/login` (dev mode: passwordless
email form; use `mpatel.mi24@gmail.com`, the default admin). After sign-in the
dashboard loads.

Prod: `https://cheapsawari.web.app` (Google sign-in, invite-only).

## 2. A representative tour

1. **Add** a round-trip: Trip=Round-trip, DTW→AMS, pick dates (note: clicking anywhere
   on a date field opens the calendar; return can't precede departure; no past dates),
   ± days = 3, Alert −% = 8 → "+ Track".
2. Card appears: route `DTW ⇄ AMS`, "no data yet" badge. Click **↻ Refresh** — with
   the mock provider a snapshot records and the price/legs line renders (with the
   pseudo-airline and the Aviasales / Google Flights / airline links when the carrier
   is mapped).
3. **Details** → leg table (every configured leg, even before data), booking-links
   legend, "Log a price (manual)": enter 900 three times, then 365 → card shows
   `▼ Bucket reopened −59.44%` and the sparkline turns green.
4. **Edit** → form pre-fills with a banner; change the destination → "Save changes"
   (issues a PUT; history kept).
5. **🎨 Theme** cycles Midnight → Nord → Forest → Daylight → Sepia; reload the page —
   the choice persists with no flash.
6. Header **↻ Reload** re-pulls and re-renders only (no fare fetched).

## 3. Automated checks

```bash
cd bruno/cheapsawari && bru run dashboard --env local   # route returns HTML
```

Visual verification standard for UI slices is headless Playwright with zero console
errors (see the Slice 15–20 changelog rows for the exact scenarios exercised).
