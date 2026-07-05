# Implementation Plan: Dashboard SPA

**Branch**: `retro/006-dashboard-spa` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slices 5 (2026-06-23), 15/16 (2026-06-25),
17/18/19/20 (2026-06-26).

## Summary

`src/web/dashboard.html` (~840 lines) is the entire frontend: CSS custom-property
themes selected by `data-theme` on `<html>`, a single add/edit form with trip-type
switching and a multi-city leg builder, cards with inline-SVG sparklines and signal
badges, a Details modal (leg table mirroring `resolved_legs`, booking links, manual
price log), and delegated event handlers for refresh/details/edit/delete. Served by
FastAPI as a `FileResponse` at `/` behind the auth redirect; its only server touchpoint
beyond the JSON API is `/health`'s `provider` + `marker` fields.

## Technical Context

**Language/Version**: vanilla ES2020+ JavaScript, CSS custom properties, inline SVG —
no framework, no build step, no CDN (Slice 5 changelog)

**Primary Dependencies**: none (deliberate); backend serves it via
`FileResponse` (`src/main.py:78-94`)

**Storage**: client-side only `localStorage["cs_theme"]` (`dashboard.html:9,772`);
all data via the JSON API

**Testing**: Bruno `dashboard/get_dashboard.bru` (route contract); headless Playwright
per UI slice with a zero-console-errors bar (changelog rows 15–20)

**Target Platform**: evergreen desktop/mobile browsers over the same origin
(cheapsawari.web.app / Cloud Run URL / 127.0.0.1:8050)

**Project Type**: web app frontend (single file) inside the web-service repo

**Performance Goals**: initial render = 1 + N×2 parallel fetches (watches, then
snapshots+signal per watch, `dashboard.html:461-467`) — fine at personal scale

**Constraints**: $0/mo — no separate hosting/build; must stay one file; native
controls must stay legible per theme (`color-scheme`)

**Scale/Scope**: 1 HTML file (~840 lines), 2 config surfaces (`marker` on /health)

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** The dashboard's full slice history is
  mapped in one rich row (`Project_Structure.md:53`) and every UI slice logged its
  changelog row; frontend↔backend traceability maintained in `Function_Mapping.md`
  (Slice 15/16/18/19 rows there).
- **II. Pattern Reference Integrity — PASS.** Full-Stack Traceability Mapping pattern
  followed (Function_Mapping.md updated per slice); no new frontend stack was
  introduced — consistent with the resolved single-$0-service identity decision.
- **III. Automated Maintenance via Agentic Skills — PASS.** verify_structure keeps the
  file logged; no generated assets to drift.
- **IV. Continuous API Validation (Bruno) — PASS with documented nuance.** The
  constitution's definition of done requires visual verification for dashboard
  changes: every UI slice ran headless Playwright (zero console errors) while the
  Bruno gate stayed green/unchanged (97/242/13) since no API surface changed (only
  Slice 18 touched `/health`, whose existing assertions still pass — changelog).
- **V. Infrastructure-as-Code & Cost Gating — PASS.** No infra: same service serves
  the file; every UI slice's cost review recorded $0.

## Project Structure

### Documentation (this feature)

```text
specs/006-dashboard-spa/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    └── ui-api-contract.md
```

### Source Code (repository root)

```text
src/
├── web/dashboard.html         # the whole frontend
│   ├── :12-47   five theme palettes + color-scheme          (S16)
│   ├── :49-56   [hidden] enforcement + picker cursor        (S15)
│   ├── :62-67   sticky header                               (S18)
│   ├── :183-218 add/edit form + multi-city builder          (S5/S7/S9/S15/S16)
│   ├── :223-236 Details modal shell                         (S15)
│   ├── :249-317 airlines, aviasales/google/site book links  (S18/S20)
│   ├── :319-331 watchLegs (resolved_legs mirror)            (S15)
│   ├── :349-374 sparkline + badges                          (S5)
│   ├── :492-561 date-picker UX (showPicker + floors)        (S17)
│   ├── :563-656 submit (POST/PUT) + edit mode               (S15)
│   ├── :658-761 Details modal + manual price log            (S15/S19)
│   └── :763-833 reload, themes, logout, card actions        (S5/S16)
├── main.py:84-94              # GET / auth-gated FileResponse (S5/S6)
├── main.py:112-120            # /health marker exposure       (S18)
└── config.py:53-56            # TRAVELPAYOUTS_MARKER          (S18)
```

**Structure Decision**: single-file SPA served by the API — the smallest shape that
keeps the product one $0 deployable; state is one in-memory map keyed by watch id.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| One 840-line HTML file instead of components | no build step/CDN/deps is a standing constraint; every slice appended to the same file | a bundler/framework rejected: adds a second toolchain and deploy artifact to a $0 single-service product |
| Client-side mirror of `resolved_legs` (`watchLegs`) | Details must show configured legs BEFORE any snapshot exists | asking the backend for resolved legs rejected — a new endpoint for data the client already holds; mirror is 12 lines with the backend as reference (`src/models.py:149-163`) |
| Three search links instead of one booking deep link | no provider exposes a bookable fare token — any single link would mislead | linking only the OTA rejected by the owner (product goal: traveler outcome over affiliate revenue — Slice 20) |
