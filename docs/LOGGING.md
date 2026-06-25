# Logging & Observability

How cheapsawari logs, what it logs, and how to search it in GCP.

## How it works (`src/obs.py`)
- **On Cloud Run** every app log line is a JSON object → Cloud Logging parses it into
  `jsonPayload.*`, so you query **by field** (not substring). Each line has `severity`,
  `message` (= the event name), `logger`, `event`, plus that event's fields.
- **Locally** the same events print as compact text: `LEVEL  logger  event  k=v k=v`.
- **Verbosity** is env-controlled: set `LOG_LEVEL` (`DEBUG|INFO|WARNING|ERROR`, default
  `INFO`) on the service to log more or less — no code change.
- Only the `cheapsawari.*` logger tree is ours; uvicorn's request/access logs are separate
  (Cloud Run also emits its own `httpRequest` logs with status/latency/IP).

> **Blind spot (by design):** a sign-in that **Google** blocks upstream (e.g. the OAuth
> consent screen in "Testing" mode) never reaches the app, so it produces **no** app log.
> Only app-side decisions appear here. If a user is allowlisted but can't log in and there's
> no `auth.login denied` line for them, the block is at Google — fix the consent screen.

## Event catalog
| event | logger | severity | when | key fields |
| :--- | :--- | :--- | :--- | :--- |
| `auth.login` | auth | INFO ok / WARNING denied | every sign-in attempt that reaches the app | `outcome` (ok\|denied), `provider` (google\|dev), `email`, `admin`, `reason` (missing_credential\|invalid_token\|not_allowlisted\|bad_email) |
| `auth.logout` | auth | INFO | sign-out | `email` |
| `auth.allowlist` | auth | INFO | admin adds/removes a user | `action` (add\|remove), `email`, `by` |
| `watch.create` | watch | INFO | a watch is created | `watch_id`, `owner`, `trip_type`, `route`, `legs` |
| `watch.delete` | watch | INFO | a watch is deleted | `watch_id`, `owner`, `by` |
| `provider.error` | provider | WARNING | a fare-provider call failed | `op` (refresh\|poll), `watch_id`, `provider`, `detail` |
| `poll.run` | poll | INFO | once per scheduled/manual poll (the daily heartbeat) | `active_watches`, `polled`, `recorded`, `no_inventory`, `errors`, `skipped_over_cap`, `alerts_fired` |
| `alert.fired` | poll | INFO | a "bucket reopened" alert was delivered | `watch_id`, `drop_pct`, `price` |
| `alert.error` | poll | WARNING | alert delivery failed | `watch_id`, `detail` |
| `poll.watch_error` | poll | ERROR | detection/store hiccup on one watch (run continues) | `watch_id`, `exception` |

## Searching in GCP — Logs Explorer (query language)
Base filter for all of our structured events:
```
resource.type="cloud_run_revision"
resource.labels.service_name="cheapsawari-api"
jsonPayload.event=~".+"
```

**Failed sign-ins** (the access-troubleshooting query):
```
resource.type="cloud_run_revision"
resource.labels.service_name="cheapsawari-api"
jsonPayload.event="auth.login"
jsonPayload.outcome="denied"
```

**Everything for one user** (sign-ins, allowlist changes, their watches won't carry email but logins do):
```
resource.labels.service_name="cheapsawari-api"
jsonPayload.email="friend@gmail.com"
```

**Daily poll health** — and runs that hit provider errors:
```
jsonPayload.event="poll.run"
# add: jsonPayload.errors>0
```

**Any provider failure:**
```
jsonPayload.event="provider.error"
```

**Anything that needs attention** (warnings + errors from our code):
```
jsonPayload.logger=~"^cheapsawari" severity>=WARNING
```

**Allowlist changes** (audit who granted/revoked access):
```
jsonPayload.event="auth.allowlist"
```

## Searching via gcloud
```bash
# Denied logins in the last 7 days, as a table:
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="cheapsawari-api" AND jsonPayload.event="auth.login" AND jsonPayload.outcome="denied"' \
  --project cheapsawari --limit 50 --freshness=7d \
  --format="table(timestamp, jsonPayload.email, jsonPayload.provider, jsonPayload.reason)"

# Last 14 daily polls:
gcloud logging read \
  'resource.labels.service_name="cheapsawari-api" AND jsonPayload.event="poll.run"' \
  --project cheapsawari --limit 14 --freshness=30d \
  --format="table(timestamp, jsonPayload.recorded, jsonPayload.no_inventory, jsonPayload.errors, jsonPayload.alerts_fired)"
```

## Changing what's logged
- **More/less detail globally:** set `LOG_LEVEL` on the Cloud Run service (e.g. `DEBUG`).
- **Add a field to one event:** add a kwarg at the `obs.event(...)` call site — it appears as
  `jsonPayload.<field>` automatically; no formatter/schema change.
- **Add a new event:** `obs.event(obs.get_logger("<domain>"), "<domain>.<action>", **fields)`,
  then add a row to the catalog above.
- **Add a field to *every* event** (e.g. a request/trace id): set it in a contextvar and merge
  it inside `_JsonFormatter.format` in `src/obs.py` — one place, no call-site churn.
