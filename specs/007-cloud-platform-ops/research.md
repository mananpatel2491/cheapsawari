# Research: Cloud Platform & Ops

As-built record — decisions reconstructed 2026-07-05 from Slice 3b/10/11/12 changelog
rows, terraform comments, and docs/DEPLOYMENT.md.

## Decision 1 — Cloud Run + Firestore + Cloud Scheduler as the whole platform

**Choice**: one scale-to-zero service, one serverless DB, one cron job (Slice 3b).
**Why**: personal scale + ~$0/mo standing budget; everything sits in free tiers
(`docs/DEPLOYMENT.md:83-90`).
**Rejected**: GKE/VMs (cost/ops), Cloud Functions split (the app is one FastAPI
process; splitting adds cold-start seams for nothing).

## Decision 2 — Public invoker + app-level gate, POLL_TOKEN for the machine path

**Choice**: `allUsers` may invoke; the app enforces Google sign-in (spec 005) and the
poll endpoint takes a shared-secret header (`terraform/main.tf:63-70`;
`docs/DEPLOYMENT.md:9`).
**Why**: Cloud IAP or IAM-gated invocation would break the public login page and cost
more setup; the two real surfaces (humans, scheduler) each have a fitting gate.

## Decision 3 — Terraform manages the platform, NOT the Cloud Run service (Slice 10)

**Choice**: enabled APIs, Firestore DB, runtime-SA IAM, invoker binding, scheduler in
terraform; the service is a read-only data source; app deploys stay
`gcloud run deploy --source .` (`terraform/main.tf:1-12,55-60`).
**Why**: image/env/revisions churn with every feature — terraform ownership would
constantly fight the deploy flow; the durable platform changes rarely and is exactly
what IaC should pin. Import-first (`import.sh`) because everything already existed.
**Rejected**: full-service management (drift wars), no IaC (Pattern 5 debt — the
Slice 3b row explicitly tracked it until Slice 10 resolved it).

## Decision 4 — Firebase Hosting rewrite for the friendly URL (Slice 12)

**Choice**: Hosting site `cheapsawari` with a single `**` rewrite to the Cloud Run
service; empty `public/` (`firebase.json`).
**Why**: `cheapsawari.web.app` for free, TLS included, no second deployable — all
traffic still lands on the one service; the Cloud Run URL stays valid (scheduler keeps
targeting it directly).
**Consequences discovered**: Hosting forwards only the `__session` cookie (drove the
spec-005 Slice-14 fix), and GIS needs the new origin whitelisted manually on the OAuth
client (`docs/DEPLOYMENT.md:50-60`).
**Rejected**: a custom domain (cost/DNS for an invite-only circle), serving static
assets from Hosting (would split the app in two).

## Decision 5 — Dependency-free structured logging keyed on K_SERVICE (Slice 11)

**Choice**: `src/obs.py` — JSON formatter when `K_SERVICE` is set (Cloud Logging
parses `jsonPayload.*`), compact text locally; one handler on the `cheapsawari` logger
tree with `propagate=False`; `event(logger, name, **fields)` as the single emission
API; `LOG_LEVEL` env knob (`src/obs.py:34-35,83-115`).
**Why**: field-level queries in Logs Explorer ARE the app's observability at $0;
arbitrary kwargs mean adding detail is a call-site one-liner. Proven immediately: the
Slice-14 cookie bug was diagnosed purely from `auth.login` events.
**Rejected**: structlog/loguru (dependency for ~100 lines), Cloud Logging client
library (stdout JSON is the Cloud Run-native path).
**Documented limitation**: sign-ins blocked upstream by Google (consent screen in
Testing mode) never reach the app and thus never log (`src/main.py:43-45`;
`docs/LOGGING.md:18`).

## Decision 6 — Runbooks as first-class docs

**Choice**: `docs/DEPLOYMENT.md` (live resources, env recovery, redeploy/rollback,
cost review) and `docs/LOGGING.md` (event catalog + copy-paste queries).
**Why**: the repo IS the ops team; env values are recoverable via
`gcloud run services describe` after `.deploy.local` was retired.
**Known drift (found during this retro conversion — report, don't fix here)**:
DEPLOYMENT.md still says "Current revision: cheapsawari-api-00008-vr7" and
`ALERT_CHANNEL=log`, but later slices shipped rev 00018-9bw and the email channel went
live 2026-06-26 (rev 00015-mv9) — the runbook lags the changelog.
