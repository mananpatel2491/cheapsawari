---
description: "As-built task record for the cloud platform & ops layer"
---

# Tasks: Cloud Platform & Ops

As-built record — reconstructed 2026-07-05 from Slices 3b (2026-06-22) and 10/11/12
(2026-06-25). `[X]` = shipped; `[ ]` = genuinely open.

## Phase 1: Cloud wiring (US1)

- [X] T001 [US1] `Dockerfile` + `.dockerignore`: python:3.13-slim, uvicorn on `$PORT`,
  context = src/ + requirements (Slice 3b)
- [X] T002 [US1] Firestore store + factory branch + `gcp_project` setting (Slice 3b;
  store detail in spec 002)
- [X] T003 [US1] Deploy Cloud Run `cheapsawari-api` (us-central1,
  WATCH_STORE=firestore, POLL_TOKEN-guarded) + Cloud Scheduler daily poll (08:00
  America/Detroit); full Bruno gate green against real Firestore; live
  scheduler→poll→snapshot confirmed (Slice 3b)
- [X] T004 [US1] Prod provider flip to Travelpayouts (rev 00004-kht, 2026-06-24 —
  spec 001 T012)

## Phase 2: Infrastructure-as-Code (US2)

- [X] T005 [US2] `terraform/versions.tf|variables.tf|main.tf|outputs.tf`: APIs,
  Firestore, runtime-SA IAM, public invoker, scheduler; Cloud Run as data source;
  sensitive `poll_token` (Slice 10)
- [X] T006 [US2] `terraform/import.sh` adoption flow + `terraform/.gitignore` (state +
  tfvars out of git); fmt/validate clean, plan green vs live GCP (Slice 10)
- [X] T007 [US2] Runbook updates: terraform README (manages/excludes, import flow,
  cost), DEPLOYMENT.md Pattern-5-done (Slice 10)

## Phase 3: Friendly URL (US3)

- [X] T008 [US3] `firebase.json` + `.firebaserc` + empty `public/`: Hosting site
  `cheapsawari` rewrites `**` → Cloud Run; deployed via `firebase deploy --only
  hosting`; live proxy checks green (Slice 12)
- [X] T009 [US3] Owner action recorded: add web.app/firebaseapp.com origins to the
  OAuth client (GIS manual-origins gotcha documented, `docs/DEPLOYMENT.md:42-60`)
  (Slice 12)

## Phase 4: Observability (US4)

- [X] T010 [US4] `src/obs.py`: JSON-on-Cloud-Run / text-local formatters, isolated
  `cheapsawari` logger tree, `event()` API, `LOG_LEVEL` (Slice 11)
- [X] T011 [US4] Instrument the critical flows: auth.login/logout/allowlist,
  watch.create/update/delete, provider.error, poll.run, alert.fired/error,
  poll.watch_error (Slice 11; watch.update added Slice 15)
- [X] T012 [US4] `docs/LOGGING.md`: event catalog + Logs Explorer/gcloud queries incl.
  the failed-sign-ins troubleshooting query + the upstream-block caveat (Slice 11)

## Open follow-ups (genuinely pending)

- [ ] T013 Move app secrets (POLL_TOKEN, TRAVELPAYOUTS_TOKEN, SESSION_SECRET,
  GOOGLE_CLIENT_ID, SMTP_PASSWORD) to Secret Manager (`docs/DEPLOYMENT.md:100-101`)
- [ ] T014 Remote terraform state (GCS backend stanza prepared but commented,
  `terraform/versions.tf:12-16`) — only needed if the project gains a second operator
- [ ] T015 Refresh `docs/DEPLOYMENT.md`: revision line (00008-vr7 → 00018-9bw era) and
  `ALERT_CHANNEL` (log → email live since 2026-06-26) — runbook lags the changelog
  (drift found during this retro conversion)
