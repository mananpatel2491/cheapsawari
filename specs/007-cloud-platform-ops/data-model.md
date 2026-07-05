# Data Model: Cloud Platform & Ops

No application entities. The "data" here is the platform inventory, the log-event
envelope, and the ops config surface.

## Live platform inventory (terraform-managed unless noted)

| Resource | Identity | Source |
|---|---|---|
| Enabled APIs | run, firestore, cloudscheduler, cloudbuild, artifactregistry, iam, iamcredentials | `terraform/main.tf:14-35` |
| Firestore DB | `(default)`, FIRESTORE_NATIVE, us-central1 | `terraform/main.tf:38-45` |
| Runtime SA IAM | `444653658968-compute@developer.gserviceaccount.com` → `roles/datastore.user` | `terraform/main.tf:49-53` |
| Cloud Run service | `cheapsawari-api` (us-central1) — DATA SOURCE, deployed by gcloud | `terraform/main.tf:55-60` |
| Public access | `allUsers` → `roles/run.invoker` | `terraform/main.tf:63-70` |
| Scheduler job | `cheapsawari-daily-poll`, `0 8 * * *` America/Detroit, POST `{uri}/api/v1/poll`, header `X-Poll-Token` | `terraform/main.tf:73-91` |
| Hosting (not TF) | site `cheapsawari` → rewrite `**` to the service | `firebase.json` |

Outputs: run URL, DB descriptor, scheduler descriptor, enabled services
(`terraform/outputs.tf`).

## Structured log envelope (`src/obs.py:50-66`)

```json
{ "severity": "INFO|WARNING|ERROR|…", "message": "<event name>",
  "logger": "cheapsawari.<domain>", "event": "<domain.action>", "<field>": "…" }
```

Reserved keys are prefixed `field_` on collision (:47,62-63); exceptions appended as
`exception`. Local format: `LEVEL  logger  event  k=v k=v` (:69-80).

## Event catalog (emitters in code; documented in `docs/LOGGING.md:23-31`)

| Event | Emitter |
|---|---|
| `auth.login` / `auth.logout` / `auth.allowlist` | `src/main.py:147-162,177-186,195,215,230` |
| `watch.create` / `watch.update` / `watch.delete` | `src/main.py:293-295,335-337,350` |
| `provider.error` | `src/main.py:370-371` (refresh), `src/poll.py:81-82` (poll) |
| `poll.run` (daily heartbeat) / `alert.fired` / `alert.error` / `poll.watch_error` | `src/poll.py:109-116,128` |

## Ops config surface

| Key | Where | Notes |
|---|---|---|
| `LOG_LEVEL` | app env (default INFO) | `src/obs.py:89` |
| `K_SERVICE` | set by Cloud Run | switches JSON logging + Secure cookie (`src/obs.py:35`; `src/main.py:69`) |
| `PORT` | injected by Cloud Run (8080) | `Dockerfile:20-21` |
| Cloud Run env | FARE_PROVIDER, TRAVELPAYOUTS_*, WATCH_STORE, POLL_TOKEN, AUTH_MODE, GOOGLE_CLIENT_ID, SESSION_SECRET, ADMIN_EMAIL, SMTP_*/ALERT_* | recoverable via `gcloud run services describe` (`docs/DEPLOYMENT.md:21-23`) |
| `TF_VAR_poll_token` / terraform.tfvars (gitignored) | terraform | sensitive (`terraform/variables.tf:49-53`) |
