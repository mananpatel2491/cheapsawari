# Research: Dashboard SPA

As-built record — decisions reconstructed 2026-07-05 from Slice 5/15–20 changelog rows
and the file itself.

## Decision 1 — Self-contained single file, served by the API (Slice 5)

**Choice**: vanilla JS + inline SVG in one HTML file, `FileResponse` at `GET /`
(`src/main.py:76-94`).
**Why**: the whole product stays one $0 Cloud Run service — no frontend build, no
hosting artifact, no dependency; sparklines are 15 lines of SVG (`dashboard.html:350-365`).
**Rejected**: React/Vue + bundler (second toolchain), separate static hosting
(deploy split for zero benefit at personal scale).

## Decision 2 — `[hidden]` + `!important` for section toggling (Slice 15 bug fix)

**Context**: `.add label { display:flex }` out-specified the UA `[hidden]` rule, so
"hidden" Return fields and the multi-city builder still showed for one-way; the dark
theme also made the native calendar icon invisible.
**Choice**: global `[hidden]{display:none!important}` + `color-scheme` so native
controls theme themselves (`dashboard.html:49-56`; per-theme `color-scheme`
:12-47 — which retired the Slice-15 icon-invert hack at Slice 16).
**Why**: attribute-driven visibility keeps JS trivial (`el.hidden = …`) and the CSS
rule guarantees it.

## Decision 3 — Edit reuses the add form (Slice 15)

**Choice**: `startEdit` pre-fills the form, flips a banner + button label, and submit
branches to PUT (`dashboard.html:597-656`).
**Why**: one validation path, one leg-builder, zero duplicated markup; matches the
backend's create-parity PUT (spec 002 Decision 6).
**Rejected**: a separate edit modal (duplicate form logic drifting from add).

## Decision 4 — Theme system as CSS custom properties + `data-theme` (Slice 16)

**Choice**: five palettes on `html[data-theme=…]`, cycled by one button, persisted in
localStorage, applied by a no-flash inline head script (`dashboard.html:7-10,12-47,
766-779`).
**Why**: zero-dependency theming; `color-scheme` per palette keeps `<input type=date>`
popups legible in both light and dark skins.

## Decision 5 — Reload vs Refresh split (Slice 16 UX rename)

**Choice**: header **Reload** = re-pull + re-render only; per-card **↻ Refresh** =
genuine `POST .../refresh` live fetch (`dashboard.html:179,441,786-823`).
**Why**: the old single "Refresh" implied live data but only re-rendered — an honesty
fix. The no-data message explains Travelpayouts cache sparsity verbatim (:809-811) and
is set AFTER `load()` so it isn't wiped (ordering bug noted in code, :804-806).

## Decision 6 — Date floors + click-anywhere pickers (Slice 17)

**Choice**: delegated `showPicker()` on any date-input click (guarded); `min`
attributes synced so departure ≥ today, return ≥ departure, leg N ≥ leg N−1, with
floors relaxing to existing values when editing past-dated watches
(`dashboard.html:492-561`).
**Why**: native constraint attributes over custom validation — the browser enforces
and communicates them; edit mode must not invalidate history.

## Decision 7 — Three labelled booking links, marker optional (Slices 18/20)

**Context**: Travelpayouts returns airline+route+date but NO bookable fare token —
any link is a *search*. Slice 18 shipped an Aviasales deep link; the owner pushed back
on linking only an OTA.
**Choice**: `bookLinks()` renders Aviasales ("most accurate match to the shown
price"), Google Flights ("compare; price may change"), and the airline's official site
from a 38-carrier map ("book direct; re-enter details"), plus a visible legend in
Details (`dashboard.html:296-317`). Aviasales URLs encode dates as DDMM and append the
affiliate `marker` only when `/health` exposes one (`:263-269`; config
`src/config.py:53-56` — public by design, not a secret).
**Why**: the product goal — personal invite-only tool optimizing the traveler's
outcome, NOT an OTA/broker; affiliate attribution is incidental (marker null in prod).
**Rejected**: single OTA link (misleading + wrong product posture), per-airline deep
links (not reliable across carriers — Slice 20 changelog).

## Decision 8 — Manual price log in Details, no "baseline input" (Slice 19)

**Choice**: surface the existing `POST .../snapshots` endpoint as a small form (price
+ optional past date, noon-UTC timestamping); hint clarifies that the detector's
baseline is always the trailing average and that email alerts fire from the daily poll
(`dashboard.html:713-761`).
**Why**: answers "how do I set a baseline" without inventing new server state — the
dev-only $900 seed used during email testing was DB-injected, not a feature (Slice 19
changelog).
