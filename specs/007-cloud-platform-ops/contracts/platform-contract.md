# Platform Contract: runtime, scheduling, hosting, logging

The operational interfaces the app and the platform agree on.

## Container ↔ Cloud Run (`Dockerfile`)

| Aspect | Value |
|---|---|
| Base image | `python:3.13-slim` |
| Entrypoint | `uvicorn src.main:app --host 0.0.0.0 --port ${PORT}` (PORT injected, default 8080) |
| Env flags | `PYTHONUNBUFFERED=1` (stdout logs flush), `K_SERVICE` presence = "on Cloud Run" (JSON logs, Secure cookie) |
| Build context | `src/` + `requirements.txt` only (`.dockerignore`) |

## Scheduler ↔ app (`terraform/main.tf:73-91`)

| Aspect | Value |
|---|---|
| Job | `cheapsawari-daily-poll`, `0 8 * * *`, America/Detroit |
| Call | `POST {run URL}/api/v1/poll`, body `{}` (base64 in TF), `Content-Type: application/json` |
| Auth | header `X-Poll-Token: var.poll_token` — must equal the service's `POLL_TOKEN` env or the app answers 401 |
| Target | the DIRECT Cloud Run URL (from the data source), not the Hosting domain |

## Hosting ↔ service (`firebase.json`)

| Aspect | Value |
|---|---|
| Site | `cheapsawari` → `https://cheapsawari.web.app` |
| Rewrite | `**` → Cloud Run `cheapsawari-api` (us-central1); `public/` intentionally empty |
| Cookie constraint | Hosting forwards ONLY `__session` to the backend (drove spec 005 Slice 14) |
| OAuth constraint | every serving domain must be manually whitelisted on the GIS OAuth client (`docs/DEPLOYMENT.md:50-60`) |

## Terraform ↔ gcloud split (`terraform/main.tf:1-12`)

| Owner | Resources |
|---|---|
| Terraform | enabled APIs (disable_on_destroy=false), Firestore `(default)`, runtime-SA `roles/datastore.user`, `allUsers` invoker, scheduler job |
| gcloud | Cloud Run service + revisions/image/env (`gcloud run deploy --source .`); read by TF as `data.google_cloud_run_v2_service.api` |
| Adoption | pre-existing infra imported via `terraform/import.sh` before first apply |
| Secrets | `poll_token` sensitive var via TF_VAR/gitignored tfvars; state local + gitignored |

## Logging contract (`src/obs.py`)

| Aspect | Value |
|---|---|
| Emission API | `obs.event(logger, "domain.action", **fields)`; None-valued fields dropped |
| Cloud shape | one JSON object/line: `severity`, `message`, `logger`, `event`, fields → `jsonPayload.*` |
| Local shape | `LEVEL  logger  event  k=v …` |
| Isolation | handler only on the `cheapsawari` tree, `propagate=False` |
| Knob | `LOG_LEVEL` (default INFO) |
| Catalog of record | `docs/LOGGING.md` — new events must add a row there (`src/obs.py:21-23`) |
