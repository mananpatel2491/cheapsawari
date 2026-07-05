# Feature Specification: Cloud Platform & Ops — Run/Firestore/Scheduler, Hosting, IaC, Observability

**Feature Branch**: `retro/007-cloud-platform-ops` (as-built record — no branch created)

**Created**: 2026-07-05

**Status**: Shipped (Slice 3b cloud wiring LIVE, 2026-06-22; Slice 10 terraform +
Slice 11 observability + Slice 12 hosting URL, 2026-06-25)

**Input**: retro-spec conversion of Slices 3b, 10, 11, 12 — everything that turns the
FastAPI app into a running ~$0/mo product.

## Why

The tracker only matters if it runs unattended: a container on Cloud Run (scale to
zero), Firestore for durable state, Cloud Scheduler poking the daily poll, a friendly
`cheapsawari.web.app` URL via Firebase Hosting rewrites, the platform codified in
Terraform (AVF Pattern 5 — resolving the "provisioned imperatively" tech debt), and
structured JSON logging so production questions ("why did sign-in fail?", "did the
poll run?") are one Logs Explorer query — which is exactly how the Slice-14 cookie bug
was diagnosed.

## User Scenarios & Testing

### User Story 1 - The product runs itself daily at ~$0 (Priority: P1)

Cloud Scheduler POSTs `/api/v1/poll` at 08:00 America/Detroit; snapshots land in
Firestore; the service scales to zero between requests.

**Why this priority**: the unattended heartbeat is the product promise.

**Independent Test**: live scheduler→poll→snapshot path confirmed at Slice 3b
(changelog); the daily `poll.run` event is queryable (`docs/LOGGING.md:29,58`).

**Acceptance Scenarios**:

1. **Given** the container, **Then** it is `python:3.13-slim` + uvicorn binding
   `$PORT` (Cloud Run injects 8080), context limited to `src/` + requirements
   (`Dockerfile:2,20-21`; `.dockerignore`).
2. **Given** prod env, **Then** `WATCH_STORE=firestore`, `FARE_PROVIDER=travelpayouts`
   (since 2026-06-24), `POLL_TOKEN` guards the public URL
   (`docs/DEPLOYMENT.md:14-23`).
3. **Given** the scheduler job, **Then** it sends `X-Poll-Token` and body `{}` daily
   at `0 8 * * *` America/Detroit (`terraform/main.tf:73-91`;
   `terraform/variables.tf:37-47`).
4. **Given** cost review, **Then** ~$0/mo: scale-to-zero Cloud Run, Firestore/Hosting
   free tiers, 3 free scheduler jobs, free Travelpayouts data
   (`docs/DEPLOYMENT.md:83-90`).

---

### User Story 2 - The platform is code (Priority: P2)

The durable GCP platform — enabled APIs, Firestore DB, runtime-SA IAM, public-invoker
binding, scheduler job — lives in `terraform/`, with the pre-existing infra adoptable
via import.

**Why this priority**: AVF Pattern 5 gate; Slice 3b shipped imperatively and logged
the debt, Slice 10 paid it.

**Independent Test**: `terraform fmt`/`validate` clean; `plan` green against live GCP
(reads the real service; 11-to-create only while state is empty → `import.sh`
resolves) (Slice 10 changelog).

**Acceptance Scenarios**:

1. **Given** the seven services APIs, **Then** they are `google_project_service`
   resources with `disable_on_destroy=false` (`terraform/main.tf:14-35`).
2. **Given** the Cloud Run service, **Then** it is deliberately a DATA SOURCE — app
   deploys stay `gcloud run deploy --source .` so infra and app never fight
   (`terraform/main.tf:55-70`; rationale :1-12).
3. **Given** secrets, **Then** `poll_token` is a sensitive var supplied via
   `TF_VAR_poll_token`/gitignored tfvars — never committed
   (`terraform/variables.tf:49-53`; `terraform/.gitignore`).
4. **Given** existing infra, **Then** `import.sh` adopts APIs/Firestore/IAM/invoker/
   scheduler into state before plan/apply (`terraform/import.sh:1-25`).

---

### User Story 3 - One friendly URL (Priority: P2)

Users visit `https://cheapsawari.web.app`; Firebase Hosting rewrites every path to the
Cloud Run service — same single $0 backend behind both URLs.

**Why this priority**: shareable identity for the invite-only circle; also the origin
of the `__session` constraint (spec 005).

**Independent Test**: live checks at Slice 12: `/health`, `/api/v1/auth/config`,
`/api/v1/watches`→401, `/login`→200 all proxy correctly (changelog).

**Acceptance Scenarios**:

1. **Given** `firebase.json`, **Then** hosting site `cheapsawari` rewrites `**` to
   Cloud Run `cheapsawari-api` (us-central1) with an intentionally empty `public/`
   (`firebase.json:1-14`; `.firebaserc`).
2. **Given** the new domain, **Then** the OAuth client's Authorized JavaScript origins
   must include it by hand or GIS won't render (owner action recorded —
   `docs/DEPLOYMENT.md:42-60`).
3. **Given** the scheduler, **Then** it still targets the Cloud Run URL directly
   (Hosting is a user-facing convenience) (Slice 12 changelog).

---

### User Story 4 - Production questions are one query (Priority: P2)

Every significant event is a structured JSON log line on Cloud Run
(`jsonPayload.event=…`), compact text locally.

**Why this priority**: a $0 app has no APM; logs are the only observability — and they
paid off immediately (Slice 14 diagnosis).

**Independent Test**: in-process + live-uvicorn verification of the JSON envelope
(Slice 11 changelog); query catalog in `docs/LOGGING.md`.

**Acceptance Scenarios**:

1. **Given** Cloud Run (`K_SERVICE` set), **Then** one JSON object per line with
   `severity`/`message`/`event` + arbitrary fields; locally compact text
   (`src/obs.py:34-35,50-80`).
2. **Given** configuration, **Then** only the `cheapsawari` logger tree is touched
   (`propagate=False` — never fights uvicorn), level via `LOG_LEVEL`
   (`src/obs.py:83-96`).
3. **Given** the event catalog, **Then** `auth.login/logout/allowlist`,
   `watch.create/update/delete`, `provider.error`, `poll.run`, `alert.fired/error`,
   `poll.watch_error` are all emitted at their call sites (`docs/LOGGING.md:23-31`;
   emitters across `src/main.py` / `src/poll.py`).
4. **Given** an upstream-blocked Google sign-in (consent screen in Testing mode),
   **Then** it never reaches the app and thus never logs — documented behavior
   (`src/main.py:43-45`; `docs/LOGGING.md:18`).

### Edge Cases

- **App-vs-infra split**: Cloud Run revisions/image/env are NOT in terraform state, so
  a `terraform apply` can never roll back an app deploy (`terraform/main.tf:3-8`).
- **Firestore has no cascade** — handled at the store layer (spec 002).
- **Secrets recovery**: `.deploy.local` is gone; env values recoverable via
  `gcloud run services describe` (`docs/DEPLOYMENT.md:21-23,35-37`).
- **State is local** (single-owner $0 project); a GCS backend stanza is pre-written
  but commented (`terraform/versions.tf:1-17`).

## Requirements

### Functional Requirements

- **FR-001**: The service MUST be containerized on `python:3.13-slim`, binding
  uvicorn to `$PORT` (`Dockerfile`).
- **FR-002**: Prod persistence MUST be Firestore Native `(default)` in us-central1
  with the runtime SA holding `roles/datastore.user` (`terraform/main.tf:38-53`;
  `docs/DEPLOYMENT.md:10-12`).
- **FR-003**: Public access MUST be the `allUsers`→`roles/run.invoker` binding (the
  app does its own auth gate — spec 005) (`terraform/main.tf:63-70`).
- **FR-004**: The daily poll MUST be a Cloud Scheduler job with the `X-Poll-Token`
  header matching the service's `POLL_TOKEN` (`terraform/main.tf:73-91`).
- **FR-005**: Hosting MUST rewrite all paths to the Cloud Run service; the direct
  Cloud Run URL keeps working (`firebase.json`).
- **FR-006**: App logging MUST be dependency-free structured logging via
  `obs.configure_logging()` + `obs.event(logger, name, **fields)`
  (`src/obs.py:83-115`), configured once at import (`src/main.py:42-46`).
- **FR-007**: Terraform MUST manage ONLY the durable platform, reading the Cloud Run
  service as a data source; `terraform destroy` MUST NOT disable APIs
  (`terraform/main.tf:28-35,55-60`).

### Key Entities

- **Live resources**: Cloud Run `cheapsawari-api` (us-central1), Firestore
  `(default)`, Scheduler `cheapsawari-daily-poll`, runtime SA
  `444653658968-compute@developer.gserviceaccount.com`, Hosting site `cheapsawari`
  (`docs/DEPLOYMENT.md:5-12`).
- **Structured event**: `{severity, message, logger, event, …fields}`
  (`src/obs.py:53-66`).

## Success Criteria

- **SC-001**: LIVE since Slice 3b: full Bruno gate (67/67 then) verified green against
  real Firestore; scheduler→poll→snapshot confirmed (changelog 2026-06-22).
- **SC-002**: `terraform validate` + `plan` clean against live GCP; ~$0/mo maintained
  — the config describes existing infra and provisions nothing new (Slice 10
  changelog; `docs/DEPLOYMENT.md:92-98`).
- **SC-003**: `https://cheapsawari.web.app` serves the app live (Slice 12 verification
  list); current prod revision at HEAD-of-history: `cheapsawari-api-00018-9bw`
  (Slice 20 era).
- **SC-004**: Structured logs proved diagnostic value: the Slice-14 `__session` bug
  was found entirely from `auth.login` events (changelog 2026-06-25).

## Assumptions

- GCP project `cheapsawari` (number 444653658968), region us-central1, Blaze-style
  free tiers (`terraform/variables.tf:1-23`).
- The owner deploys by `gcloud run deploy --source .` (Cloud Build) and pushes env
  flips with `--update-env-vars` (`docs/DEPLOYMENT.md:70-81`).
- Optional future hardening (documented, not done): app secrets → Secret Manager
  (`docs/DEPLOYMENT.md:100-101`).
