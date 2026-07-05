# Feature Specification: Snapshots, Poll Engine, Reopen Detection & Alert Seam

**Feature Branch**: `retro/003-snapshots-signal-alerts` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 3a poll engine, 2026-06-22; Slice 4 detection + alert seam,
2026-06-23; Slice 16b per-watch threshold, 2026-06-25)

**Input**: retro-spec conversion of Slices 3a, 4, and the Slice-16 per-watch
alert-threshold portion — the unattended heart of the tracker.

## Why

The product thesis: yield-managed inventory occasionally releases a cheaper booking
class, and the win is catching *that exact moment*. That requires (1) a price
time-series per watch — snapshots, recorded by a quota-capped daily poll or by hand;
(2) a pure detector that flags when the latest fare drops meaningfully below its
trailing average — on the rising edge only, so an unattended daily poll alerts once per
reopening instead of every day the price stays low; and (3) a swappable `AlertChannel`
seam so a detection becomes a log line, webhook POST, or email without the poll engine
knowing which.

## User Scenarios & Testing

### User Story 1 - Unattended daily poll records history (Priority: P1)

Cloud Scheduler hits `POST /api/v1/poll` daily; every active watch gets priced and
snapshotted, capped so a run can never burn the provider quota.

**Why this priority**: the unattended heartbeat — without it there is no series and no
signal.

**Independent Test**: `bruno/cheapsawari/poll/` (7 requests): two watches → poll run →
verify snapshot recorded → 401 without the token.

**Acceptance Scenarios**:

1. **Given** N active watches, **When** a run executes, **Then** at most
   `POLL_MAX_PER_RUN` (default 60) are queried and the surplus is reported as
   `skipped_over_cap` (`src/poll.py:75,124`; `src/config.py:61`).
2. **Given** one watch's provider call fails, **When** the run continues, **Then** the
   error is counted (`errors`) and logged as `provider.error`, never fatal
   (`src/poll.py:79-83`).
3. **Given** `POLL_TOKEN` is configured, **When** the header is absent/wrong, **Then**
   401 (`src/main.py:471-472`); the endpoint is otherwise open for local dev.
4. **Given** a completed run, **Then** exactly one structured `poll.run` heartbeat
   event carries the full `PollSummary` (`src/poll.py:127-128`).

---

### User Story 2 - "Bucket reopened" detection (Priority: P1)

When the latest observed price sits > threshold% below its 7-day trailing average — and
the previous point didn't — the watch fires a `bucket_reopened` signal.

**Why this priority**: the insight the tracker exists to surface.

**Independent Test**: `bruno/cheapsawari/signal/` (14 requests) seeds 110/108/112 then
90 → detected with drop_pct; a flat series → not detected; unknown watch → 404.

**Acceptance Scenarios**:

1. **Given** fewer than 3 snapshots, **When** evaluated, **Then** no signal
   (`_MIN_HISTORY`, `src/signal.py:28-31,98-99`).
2. **Given** the latest price < baseline × (1 − threshold/100) where baseline is the
   mean of prior points within `SIGNAL_WINDOW_DAYS`, **Then** a `Signal` with
   `current_price`, `baseline_price`, `drop_pct`, window/threshold, and the route from
   the triggering snapshot's legs (`src/signal.py:61-132`).
3. **Given** the *previous* point already qualified as a drop, **When** the latest also
   qualifies, **Then** NO signal — rising-edge only, no persisted alert state
   (`src/signal.py:108-111`; rationale :12-17).
4. **Given** a watch with `alert_threshold_pct` set, **When** detection runs (endpoint
   or poll), **Then** the per-watch value overrides the server default
   (`src/main.py:454-456`; `src/poll.py:99-102`; Bruno
   `notify/get_signal_custom_threshold.bru`: a 9% drop fires at a custom 8% but not at
   the 15% default).

---

### User Story 3 - Alerts through a swappable channel (Priority: P2)

After each recorded snapshot the poll re-examines the series; a fresh signal is
delivered through the configured channel (log default, webhook, email — spec 004).

**Why this priority**: detection without delivery is a dashboard-only feature; the
seam keeps delivery pluggable.

**Independent Test**: run a poll over a seeded dropping series with `ALERT_CHANNEL=log`
→ an `ALERT ✈️ Bucket reopened…` warning line + `alert.fired` event;
`PollSummary.alerts_fired` increments.

**Acceptance Scenarios**:

1. **Given** a fresh signal after a recorded snapshot, **When** the alerter is set,
   **Then** `send(signal, recipient=watch.owner_email)` is called once and
   `alerts_fired` increments (`src/poll.py:94-110`).
2. **Given** an `AlertError` (or any detection hiccup), **When** it occurs, **Then**
   it is logged (`alert.error` / `poll.watch_error`) and the run continues
   (`src/poll.py:111-116`).
3. **Given** `ALERT_CHANNEL=webhook` with a URL, **Then** the alert POSTs JSON
   `{text, signal}` (Slack/Discord-compatible) via httpx
   (`src/alerts/webhook_channel.py:23-29`); with no URL it degrades to log
   (`src/alerts/factory.py:22-28`).

---

### User Story 4 - Manual price logging / backfill (Priority: P3)

A user records a price they saw (optionally dated in the past) so a trend/reference
series exists without waiting for polls.

**Why this priority**: also the deterministic way contract tests seed a series — the
stateless mock can't produce a trend by polling (`src/models.py:229-233`).

**Independent Test**: `bruno/cheapsawari/signal/seed_*.bru` seed via
`POST .../snapshots`; UI flow in spec 006 (Slice 19).

**Acceptance Scenarios**:

1. **Given** a price (+ optional `observed_at`, `fare_basis`, `carrier`, `cabin`),
   **When** `POST /api/v1/watches/{id}/snapshots`, **Then** a snapshot tagged
   `provider="manual"` is stored, cabin defaulting to the watch's
   (`src/main.py:398-429`).
2. **Given** no baseline *input* exists anywhere, **Then** the detector's baseline is
   always the auto-computed trailing average of recorded snapshots (Slice 19 changelog
   clarification; `src/signal.py:71-75`).

### Edge Cases

- **Snapshots arrive in any order** — detection sorts by `observed_at`
  (`src/signal.py:101`).
- **No prior point inside the window** → no judgement possible, no signal
  (`src/signal.py:72-73`).
- **Round-trip/multi-city watches**: detection reads the snapshot's `price` (the trip
  total) so it works unchanged on every shape (`src/models.py:188-195`).
- **Legacy snapshots without legs** → `Signal.origin/destination` stay None; alerts
  fall back to the watch-id wording (`src/signal.py:116-119`;
  `src/alerts/base.py:22-27`).
- **Travelpayouts reality**: `fare_basis` is always None on live data, so "bucket
  reopened" operationally means "cheapest observed price dropped" (spec 001,
  research.md Decision 5).

## Requirements

### Functional Requirements

- **FR-001**: `poll_active_watches(repo, provider, max_per_run, alerter, threshold_pct,
  window_days)` MUST poll active watches once, cap at `max_per_run`, count
  recorded/no_inventory/errors/skipped, and never raise for a single watch
  (`src/poll.py:44-129`).
- **FR-002**: `POST /api/v1/poll` MUST return the `PollSummary` and enforce
  `X-Poll-Token` when `POLL_TOKEN` is set (`src/main.py:462-480`).
- **FR-003**: `detect_reopening(snapshots, threshold_pct=15.0, window_days=7)` MUST be
  pure (no I/O) and fire only on the rising edge (`src/signal.py:79-132`).
- **FR-004**: `GET /api/v1/watches/{id}/signal` MUST run on-demand detection over up to
  1000 snapshots and return a stable `SignalResult {watch_id, detected, signal}`
  (`src/main.py:434-457`; `src/signal.py:53-58`).
- **FR-005**: Alert delivery MUST go through `AlertChannel.send(signal, recipient)`;
  channels with fixed destinations ignore `recipient` (`src/alerts/base.py:37-50`).
- **FR-006**: Channel selection MUST come from `ALERT_CHANNEL` (log default | webhook |
  email) and degrade to log rather than crash when misconfigured
  (`src/alerts/factory.py:20-61`).
- **FR-007**: Defaults MUST be env-tunable: `SIGNAL_THRESHOLD_PCT=15.0`,
  `SIGNAL_WINDOW_DAYS=7`, `POLL_MAX_PER_RUN=60` (`src/config.py:61,70-71,120-125`),
  with `alert_threshold_pct` (1..90) as the per-watch override
  (`src/models.py:109-112`).

### Key Entities

- **PriceSnapshot**: the time-series row (shape in spec 002 data-model.md).
- **Signal / SignalResult**: the detection outputs (`src/signal.py:34-58`).
- **PollSummary**: the run tally (`src/poll.py:28-41`).
- **AlertChannel / AlertError**: the delivery seam (`src/alerts/base.py`).

## Success Criteria

- **SC-001**: Bruno `poll/` (7), `signal/` (14), `notify/` (7) suites green inside the
  full 97 req / 242 assert / 13 test gate.
- **SC-002**: Live scheduler→poll→snapshot path confirmed in prod at Slice 3b
  (changelog 2026-06-22); `poll.run` is the queryable daily heartbeat
  (`docs/LOGGING.md:29`).
- **SC-003**: Rising-edge semantics proven by the flat-series and re-fire Bruno cases
  (`bruno/cheapsawari/signal/get_signal_flat.bru`) — exactly one alert per reopening
  with zero persisted alert state.

## Assumptions

- Once-daily polling is enough granularity for cached fare-trend data (source refreshes
  ~2–7 days, spec 001).
- `POLL_MAX_PER_RUN=60` was sized for the dead Amadeus quota; on free Travelpayouts it
  is "now just a politeness cap" (`docs/DEPLOYMENT.md:90`).
- The poll's detection reads the default snapshot page (limit 100,
  `src/poll.py:101-102`; `src/store/base.py:120`) — ample since the baseline window is
  7 days of a daily poll.
