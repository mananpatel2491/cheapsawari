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

### Auth (Slice 6) — pending owner step to go live
The app is gated by Google sign-in + an admin-managed allowlist. The **code is deployed-ready
and verified locally in `AUTH_MODE=dev`**, but prod still runs the pre-auth revision until you
create a Google OAuth client and flip the env. Until then, do **not** set `AUTH_MODE=google`
without `GOOGLE_CLIENT_ID`, or sign-in will be unusable.

Owner one-time setup to enable real Google sign-in:
1. GCP console → **APIs & Services → Credentials → Create credentials → OAuth client ID →
   Web application**. Under **Authorized JavaScript origins** add the Cloud Run URL
   (`https://cheapsawari-api-444653658968.us-central1.run.app`) and `http://127.0.0.1:8050`
   for local. (No redirect URI needed — GIS returns the token to the page.) Copy the **Client ID**.
2. Generate a stable session secret: `python -c "import secrets;print(secrets.token_urlsafe(32))"`.
3. Redeploy with the auth env (merges, preserving existing secrets):
   ```bash
   gcloud run services update cheapsawari-api --region us-central1 --project cheapsawari \
     --update-env-vars "AUTH_MODE=google,GOOGLE_CLIENT_ID=<client-id>,SESSION_SECRET=<secret>,ADMIN_EMAIL=mpatel.mi24@gmail.com"
   ```
   `ADMIN_EMAIL` is the bootstrap owner (always allowed; the only account that can manage the
   allowlist at `/admin`). `SESSION_SECRET` MUST stay stable or live sessions invalidate on each
   deploy/instance. The Firestore `allowed_users/{email}` collection holds invited users — no
   schema/index step needed (it's created on first add).

> **Current revision:** `cheapsawari-api-00004-kht` (live Travelpayouts fares), deployed 2026-06-24.
> Auth (Slice 6) is built + gate-green but **not yet flipped on in prod** — see the owner step above.

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

## Known follow-up
Infrastructure was provisioned imperatively via `gcloud` (APIs, Firestore DB, Cloud Run,
Scheduler, IAM). Per AVF Pattern 5 (Infrastructure-as-Code & Cost Gating), codifying these
in `terraform/` is a tracked follow-up before any GitHub release tagging.
