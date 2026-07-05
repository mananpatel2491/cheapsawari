---
description: "As-built task record for snapshots, poll engine, reopen detection & alert seam"
---

# Tasks: Snapshots, Poll Engine, Reopen Detection & Alert Seam

As-built record — reconstructed 2026-07-05 from Slices 3a (2026-06-22), 4 (2026-06-23),
16b (2026-06-25). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Poll engine (US1)

- [X] T001 [US1] `src/poll.py`: `poll_active_watches` with `max_per_run` cap,
  per-watch error isolation, `PollSummary` (Slice 3a)
- [X] T002 [US1] `POST /api/v1/poll` + optional `POLL_TOKEN`/`X-Poll-Token` guard
  (Slice 3a)
- [X] T003 [US1] Bruno `poll/` suite: 7 requests incl. 401-without-token and
  snapshot-recorded verification (gate 24/67 at Slice 3a)

## Phase 2: Detection (US2)

- [X] T004 [US2] `src/signal.py`: pure `detect_reopening` — trailing-mean baseline,
  threshold, rising-edge suppression, `_MIN_HISTORY=3` (Slice 4)
- [X] T005 [US2] `GET /api/v1/watches/{id}/signal` on-demand endpoint returning
  `SignalResult` (Slice 4)
- [X] T006 [US2] Bruno `signal/` suite: 14 requests — seeded drop detected, flat series
  not detected, unknown 404, self-cleaning (Slice 4)
- [X] T007 [US2] Per-watch `alert_threshold_pct` override in endpoint + poll; Bruno
  `notify/` proof (9% drop fires at custom 8%, not at default 15%) (Slice 16)
- [X] T008 [US2] `Signal.origin/destination` from the triggering snapshot's legs so
  alerts read as a route, not a UUID (Slice 16)

## Phase 3: Alert seam (US3)

- [X] T009 [US3] `src/alerts/base.py`: `AlertChannel` ABC + `AlertError` + shared
  `render_text` (Slice 4; `recipient` parameter Slice 16)
- [X] T010 [US3] `LogAlertChannel` (default, prod-safe) + `WebhookAlertChannel`
  (httpx POST, Slack/Discord-compatible payload) (Slice 4)
- [X] T011 [US3] `src/alerts/factory.py`: `ALERT_CHANNEL` resolution with
  degrade-to-log on missing webhook URL (Slice 4; email branch Slice 16 — spec 004)
- [X] T012 [US3] Poll wiring: detect after each recorded snapshot, deliver to
  `watch.owner_email`, count `alerts_fired`, isolate `AlertError`/hiccups (Slice 4;
  recipient Slice 16)

## Phase 4: Manual logging (US4)

- [X] T013 [US4] `SnapshotCreate` model + `POST /api/v1/watches/{id}/snapshots`
  (provider='manual', backfillable `observed_at`) (Slice 4)
- [X] T014 [US4] UI surface for manual logging in the Details modal (Slice 19 —
  spec 006)

## Open follow-ups (genuinely pending)

- [ ] T015 Multi-channel fan-out (deliver one signal to several channels) — the seam
  anticipates it (`src/alerts/base.py:5-8`) but the factory returns exactly one channel
- [ ] T016 Additional signal kinds (only `bucket_reopened` exists; `Signal.kind` is
  already a field, `src/signal.py:38`)
