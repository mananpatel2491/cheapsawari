# Deployment (Slice 3b — cloud)

cheapsawari runs on Google Cloud, project **`cheapsawari`**, region **`us-central1`**.

## Live resources

| Resource | Identity | Notes |
| :--- | :--- | :--- |
| Cloud Run service | `cheapsawari-api` | URL: `https://cheapsawari-api-444653658968.us-central1.run.app`. Public (`--allow-unauthenticated`), protected by `POLL_TOKEN`. Scales to zero. |
| Firestore | `(default)`, Native mode, `us-central1` | Watches + snapshots. `watches/{id}` docs with a `snapshots/` subcollection. |
| Cloud Scheduler | `cheapsawari-daily-poll` | `POST /api/v1/poll` daily at **08:00 America/Detroit**, header `X-Poll-Token`, body `{}`. |
| Runtime SA | `444653658968-compute@developer.gserviceaccount.com` | Granted `roles/datastore.user`. |

## Deployed configuration (Cloud Run env)
- `FARE_PROVIDER=travelpayouts` — **LIVE on real fares since 2026-06-24.** (Amadeus
  Self-Service was decommissioned 2026-07-17; mock remains the default for local/tests.)
- `TRAVELPAYOUTS_TOKEN=<secret>` — Travelpayouts affiliate (Data API) token. Held in the
  Cloud Run env (same handling as POLL_TOKEN). Optional hardening: move to Secret Manager.
- `TRAVELPAYOUTS_CURRENCY=usd`
- `WATCH_STORE=firestore`
- `POLL_TOKEN=<secret>` — generated at deploy time; the same value is set on the scheduler
  header. `.deploy.local` is gone; recover any of these env values from
  `gcloud run services describe cheapsawari-api --region us-central1 --format='value(spec.template.spec.containers[0].env)'`.
- `ALERT_CHANNEL=log` (Slice 4) — alerts go to Cloud Run logs (zero-cost, prod-safe). To
  deliver outbound, set `ALERT_CHANNEL=webhook` + `ALERT_WEBHOOK_URL=<slack/discord/generic hook>`.

### Auth (Slice 6) — LIVE
The app is gated by Google sign-in + an admin-managed allowlist, **live in prod since
2026-06-24** (rev `cheapsawari-api-00005-dsk`). Deployed env:
- `AUTH_MODE=google`
- `GOOGLE_CLIENT_ID=444653658968-8gitgph8u478m6r1s7ffm1srlvivqgo5.apps.googleusercontent.com`
  — the OAuth Web client auto-created when the owner enabled Google sign-in in the Firebase
  console. Its **Authorized JavaScript origins** must include the Cloud Run URL(s) below, or
  GIS refuses to render the button.
- `SESSION_SECRET=<secret>` — generated at deploy time (`python -c "import secrets;print(secrets.token_urlsafe(32))"`).
  MUST stay stable across deploys or live sessions invalidate; recover it via
  `gcloud run services describe cheapsawari-api --region us-central1 --format='value(spec.template.spec.containers[0].env)'`.
- `ADMIN_EMAIL=mpatel.mi24@gmail.com` — bootstrap owner: always allowed, and the only account
  that can manage the allowlist at `/admin`. Invited users live in Firestore `allowed_users/{email}`
  (created on first add; no index step).

Authorized JavaScript origins on the OAuth client (all four):
- `https://cheapsawari.web.app`  ← Firebase Hosting (Slice 12)
- `https://cheapsawari.firebaseapp.com`
- `https://cheapsawari-api-444653658968.us-central1.run.app`
- `https://cheapsawari-api-p3vdiwk6kq-uc.a.run.app`

(+ `http://127.0.0.1:8050` for local dev.)

> ⚠️ **GOTCHA — every serving domain must be added by hand.** cheapsawari uses **Google Identity
> Services (GIS) directly** (the Slice 6 choice), not the Firebase Auth SDK. With GIS the token is
> issued from the *page's own origin*, so Google validates that origin against this **Authorized
> JavaScript origins** list — which is manual. **Any new domain the app is served from (a custom
> domain, another Hosting site, etc.) WILL break sign-in until you add it here.** This is unlike the
> TradeFleet sites, which use the Firebase Auth SDK: Firebase brokers OAuth through its own handler
> domain and auto-authorizes Hosting domains via *Firebase Auth → Authorized domains*, so they never
> touch the GCP OAuth client. The trade-off is deliberate (single $0 FastAPI service, no Firebase web
> SDK); the cost is this one manual step per domain. Symptom when forgotten: the "Sign in with Google"
> button doesn't render / errors, and **no `auth.login` event appears in the logs** (the block is
> upstream at Google — see `docs/LOGGING.md`).

To re-flip env later without a code change: `gcloud run services update cheapsawari-api
--region us-central1 --project cheapsawari --update-env-vars "KEY=VALUE,..."`.

> **Current revision:** `cheapsawari-api-00008-vr7` — Slices 6–8 (Google auth + allowlist,
> round-trip/flex, per-user ownership), 9 (multi-city), 11 (structured logging); served at
> **`https://cheapsawari.web.app`** via Firebase Hosting (Slice 12) and at the Cloud Run URL.
> Live Travelpayouts fares. IaC in `terraform/` (Slice 10).

## Redeploy
```bash
# --update-env-vars MERGES, preserving existing secrets (POLL_TOKEN, TRAVELPAYOUTS_TOKEN, etc.).
gcloud run deploy cheapsawari-api --source . --region us-central1 --allow-unauthenticated \
  --update-env-vars "FARE_PROVIDER=travelpayouts" --project cheapsawari
```

To roll back to mock (e.g. if the token is revoked):
```bash
gcloud run services update cheapsawari-api --region us-central1 --project cheapsawari \
  --update-env-vars "FARE_PROVIDER=mock"
```

## Cost review
~**$0/month** at personal scale: Cloud Run scales to zero (generous free tier), Firestore
free tier (1 GiB + 50k reads/20k writes per day), Cloud Scheduler (3 free jobs/month).
Live fares come from **Travelpayouts (Aviasales) Data API**, which is **free** (affiliate-token
gated, no per-call charge) — so a daily poll adds $0. Caveat: that data is **cached** (stored
~7 days, sourced from real Aviasales searches), so it is fare-*trend* data, not a guaranteed
bookable quote, and per-day cache can be sparse for less-popular routes/dates (those polls return
"no inventory" until the cache has an entry). `POLL_MAX_PER_RUN=60` is now just a politeness cap.

## Infrastructure-as-Code (AVF Pattern 5) — DONE
The platform (enabled APIs, Firestore DB, runtime-SA IAM, public-invoker binding, the
daily Cloud Scheduler job) is codified in **`terraform/`** (`terraform validate` + `plan`
clean against live GCP). The Cloud Run service + revisions stay with `gcloud run deploy
--source .` and are read by Terraform as a data source. The infra already exists, so adopt
it into state with `terraform/import.sh` before `plan`/`apply` (see `terraform/README.md`).
Cost gate: still **~$0/mo** — the config describes existing infra and provisions nothing new.

Optional future hardening: move app secrets (`POLL_TOKEN`, `TRAVELPAYOUTS_TOKEN`,
`SESSION_SECRET`, `GOOGLE_CLIENT_ID`) from Cloud Run env vars into Secret Manager.
