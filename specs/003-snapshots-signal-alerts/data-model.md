# Data Model: Snapshots, Poll Engine, Reopen Detection & Alert Seam

Persistence of the snapshot series is owned by spec 002 (storage-contract.md). Shapes
here are the detection/poll transport models and config.

## Signal (`src/signal.py:34-51`)

| Field | Type | Notes |
|---|---|---|
| `watch_id` | str | |
| `kind` | str = "bucket_reopened" | only signal type today |
| `current_price` | float | the triggering (latest) price |
| `baseline_price` | float | trailing-window mean, rounded 2dp |
| `drop_pct` | float | (baseline − current)/baseline × 100, rounded 2dp |
| `currency` / `fare_basis` | str / str\|None | from the triggering snapshot |
| `observed_at` | datetime | trigger time |
| `window_days` / `threshold_pct` | int / float | parameters used |
| `origin` / `destination` | str \| None | first/last leg of the triggering snapshot (Slice 16, :48-50) — None on legacy snapshots |

## SignalResult (`src/signal.py:53-58`)

`{watch_id, detected: bool, signal: Signal | null}` — the stable API/Bruno shape.

## PollSummary (`src/poll.py:28-41`)

`{active_watches, polled, recorded, no_inventory, errors, skipped_over_cap,
alerts_fired}` — also the payload of the `poll.run` structured event
(`src/poll.py:127-128`; `docs/LOGGING.md:29`).

## SnapshotCreate (manual logging input, `src/models.py:226-242`)

`{price (≥0, required), currency="USD", cabin?, fare_basis?, carrier?, observed_at?}` —
stored via the normal `add_snapshot` path tagged `provider="manual"`
(`src/main.py:417-429`).

## Webhook payload (`src/alerts/webhook_channel.py:24`)

```json
{ "text": "✈️ Bucket reopened for JFK→LAX: USD 365.00 (59.4% below the 7-day avg of USD 900.00)",
  "signal": { …full Signal model_dump… } }
```

`text` is `render_text(signal)` (`src/alerts/base.py:20-34`) — shared by every channel.

## Config / env keys (`src/config.py:61-71,120-125`)

| Key | Default | Effect |
|---|---|---|
| `POLL_MAX_PER_RUN` | 60 | per-run watch cap |
| `POLL_TOKEN` | unset | when set, `X-Poll-Token` required on POST /api/v1/poll |
| `ALERT_CHANNEL` | `log` | log \| webhook \| email |
| `ALERT_WEBHOOK_URL` | unset | webhook target; blank → degrade to log |
| `SIGNAL_THRESHOLD_PCT` | 15.0 | server default drop threshold |
| `SIGNAL_WINDOW_DAYS` | 7 | trailing-average window |

Per-watch override: `alert_threshold_pct` REAL column / Firestore field on the watch
(spec 002 data-model.md).
