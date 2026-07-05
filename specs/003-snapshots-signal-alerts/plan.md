# Implementation Plan: Snapshots, Poll Engine, Reopen Detection & Alert Seam

**Branch**: `retro/003-snapshots-signal-alerts` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: As-built reconstruction from Slice 3a (2026-06-22), Slice 4 (2026-06-23),
Slice 16b threshold override (2026-06-25).

## Summary

`src/poll.py:poll_active_watches` iterates active watches (capped), prices each via
`price_watch_trip`, stores a snapshot, then re-runs `src/signal.py:detect_reopening`
on the freshly extended series and fires the configured `AlertChannel` on a
rising-edge drop — all failures isolated per watch. Detection is a pure function:
trailing-window mean baseline + threshold + rising-edge suppression, with the per-watch
`alert_threshold_pct` overriding the server default in both the on-demand endpoint and
the poll. The alert seam mirrors the provider/store seams: `base.py` contract +
log/webhook (+ email, spec 004) + factory with degrade-to-log behavior.

## Technical Context

**Language/Version**: Python 3.13; `statistics.mean` for the baseline (stdlib)

**Primary Dependencies**: none new — httpx (already present) for the webhook channel

**Storage**: reads/writes the spec-002 snapshot series; detection itself persists
nothing (the series is the memory, `src/signal.py:16-17`)

**Testing**: Bruno `poll/`, `signal/`, `notify/` suites (28 request files) with
deterministic manual-snapshot seeding; in-process checks per changelog rows

**Target Platform**: same single service; triggered by Cloud Scheduler in prod (spec 007)

**Project Type**: web service (background-style engine exposed as one endpoint)

**Performance Goals**: one run/day; per-run provider calls ≤ POLL_MAX_PER_RUN ×
legs × (flex+1)

**Constraints**: $0/mo — log channel default; webhook = one outbound POST; quota
protection via cap + token

**Scale/Scope**: 3 modules (~310 lines) + 3 channel files + factory (~160 lines)

## Constitution Check

Gated against `.specify/memory/constitution.md` (distillation; `GEMINI.md` supreme).

- **I. Context-First Architecture Map — PASS.** `src/poll.py`, `src/signal.py`, and
  every `src/alerts/*` file carry functional map rows (`Project_Structure.md:45-52`);
  slice changelog rows list the exact files.
- **II. Pattern Reference Integrity — PASS.** "notifications behind `AlertChannel`
  (log/webhook/email)" is a named sacred seam
  (`.specify/memory/constitution.md:29`); Slice 16 extended `send()` with `recipient`
  instead of adding a parallel path.
- **III. Automated Maintenance via Agentic Skills — PASS.** No manual state: alert
  dedup needs no store (rising edge), migrations are automatic (spec 002).
- **IV. Continuous API Validation (Bruno) — PASS.** `poll/` (24/67 gate at Slice 3a),
  `signal/` (14 requests incl. flat/re-fire cases), `notify/` (custom-threshold proof);
  all inside the current 97/242/13.
- **V. Infrastructure-as-Code & Cost Gating — PASS.** The daily trigger (Cloud
  Scheduler) is codified in `terraform/main.tf:73-91` (spec 007); Slice 4 cost review:
  $0 (log channel; webhook one POST). Quota protection is a first-class design input
  (`src/poll.py:7-11`).

## Project Structure

### Documentation (this feature)

```text
specs/003-snapshots-signal-alerts/
├── spec.md
├── plan.md              # this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
└── contracts/
    ├── alert-channel-contract.md
    └── openapi-poll-signal.yaml
```

### Source Code (repository root)

```text
src/
├── poll.py                    # quota-capped engine + PollSummary + alert wiring (S3a; alerts S4; threshold S16)
├── signal.py                  # pure detect_reopening + Signal/SignalResult      (S4; route fields S16)
├── main.py:398-480            # manual snapshot POST, /signal, /poll routes      (S4; S3a)
└── alerts/
    ├── base.py                # AlertChannel ABC + AlertError + render_text      (S4; recipient arg S16)
    ├── log_channel.py         # default zero-cost channel                        (S4)
    ├── webhook_channel.py     # Slack/Discord/generic incoming-webhook POST      (S4)
    ├── email_channel.py       # owner-targeted email                             (S16 — spec 004)
    └── factory.py             # ALERT_CHANNEL resolution + degrade-to-log        (S4; email branch S16)
```

**Structure Decision**: detection kept pure and store-free so the on-demand endpoint
and the poll share it verbatim; delivery isolated behind the third seam of the app.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Rising-edge logic needs ≥3 snapshots and a double evaluation | one alert per reopening with NO persisted alert state | a `last_alerted_at` column was rejected — more schema, more migration, and replay/backfill would corrupt it; the series itself is the memory (`src/signal.py:12-17`) |
| Broad `except Exception` in the poll's detect/alert block | a store/detection hiccup on one watch must not sink the daily run | letting it propagate was rejected: the scheduler retries would re-price everything; error is logged with `exc_info` (`src/poll.py:114-116`) |
