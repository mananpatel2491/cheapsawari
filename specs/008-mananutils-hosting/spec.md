# Spec 008 — Move cheapsawari into the shared `mananutils` project

**Kind:** infrastructure (no API or behaviour change). **Status:** in progress. **Decided:**
2026-10-18 by the Director: consolidate personal-app hosting into GCP project `mananutils`
(hub-and-spoke), and give cheapsawari the same full setup as family-atlas.

## Why
- One project, one console, one budget. Deleting project `cheapsawari` frees a slot on the main
  billing account (capped at 5 projects) so the last stray project can join it.
- The repo is public; secrets move out of Cloud Run env vars into Secret Manager.
- Deploys become repeatable: `v*` tag → GitHub Actions → Cloud Run, keyless (shared WIF pool).

## Requirements
1. Same app and behaviour: Google sign-in + allowlist, watches, daily poll with `X-Poll-Token`,
   email alerts, live Travelpayouts fares.
2. Data moves intact: every document in `cheapsawari/(default)` lands in `mananutils/cheapsawari`.
3. Isolation in the shared project: own named database (runtime SA limited to it by an IAM
   condition), own secrets (`CHEAPSAWARI_*`), own service accounts and Hosting site.
4. Terraform owns all infrastructure, including the Cloud Run service's env and secrets; CI only
   swaps the image. State in `gs://mananutils-tfstate-2491/cheapsawari`.
5. The old project keeps serving until the new one is verified; then its scheduler is paused and the
   project deleted.

## Code change
`FIRESTORE_DATABASE` setting (default `(default)`), passed to both Firestore repositories. Local
dev and the Bruno gate are unchanged (SQLite).

## Success criteria
- `https://cheapsawari-mananutils.web.app` signs in, shows existing watches, and edits persist.
- A manual scheduler run (`gcloud scheduler jobs run cheapsawari-daily-poll --location us-central1
  --project mananutils`) logs a successful poll.
- Deploy workflow passes on a `v*` tag (auth, push, deploy, `/health` smoke check).
