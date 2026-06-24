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
- `FARE_PROVIDER=mock` — **deployed on mock to prove the pipeline.** Flip to `amadeus`
  (and set `AMADEUS_CLIENT_ID` / `AMADEUS_CLIENT_SECRET`) once those keys are in hand.
- `WATCH_STORE=firestore`
- `POLL_TOKEN=<secret>` — generated at deploy time; the same value is set on the scheduler
  header. `.deploy.local` is gone; recover the value from
  `gcloud run services describe cheapsawari-api --region us-central1 --format='value(spec.template.spec.containers[0].env)'`.
- `ALERT_CHANNEL=log` (Slice 4) — alerts go to Cloud Run logs (zero-cost, prod-safe). To
  deliver outbound, set `ALERT_CHANNEL=webhook` + `ALERT_WEBHOOK_URL=<slack/discord/generic hook>`.

> **Current revision:** `cheapsawari-api-00002-bmv` (Slice 4 — signal detection + alerts), deployed 2026-06-23.

## Redeploy
```bash
# POLL_TOKEN: recover from the running service (see above) into $POLL_TOKEN, then:
gcloud run deploy cheapsawari-api --source . --region us-central1 --allow-unauthenticated \
  --set-env-vars "FARE_PROVIDER=mock,WATCH_STORE=firestore,POLL_TOKEN=${POLL_TOKEN},ALERT_CHANNEL=log" \
  --project cheapsawari
```

To switch to live fares later:
```bash
gcloud run services update cheapsawari-api --region us-central1 --project cheapsawari \
  --update-env-vars "FARE_PROVIDER=amadeus,AMADEUS_CLIENT_ID=...,AMADEUS_CLIENT_SECRET=..."
```

## Cost review
~**$0/month** at personal scale: Cloud Run scales to zero (generous free tier), Firestore
free tier (1 GiB + 50k reads/20k writes per day), Cloud Scheduler (3 free jobs/month).
When live fares are enabled, one scheduled poll/day with `POLL_MAX_PER_RUN=60` is meant
to stay under the Amadeus Self-Service free quota — but that quota is **per-API and varies**
(~200–10k/mo; no single flat number). Confirm the Flight Offers Search figure in your Amadeus
account Workspace and re-size `POLL_MAX_PER_RUN` to fit. Overage is pay-per-call (~€0.0008–0.025);
the test environment also serves limited/cached data, not full live inventory.

## Known follow-up
Infrastructure was provisioned imperatively via `gcloud` (APIs, Firestore DB, Cloud Run,
Scheduler, IAM). Per AVF Pattern 5 (Infrastructure-as-Code & Cost Gating), codifying these
in `terraform/` is a tracked follow-up before any GitHub release tagging.
