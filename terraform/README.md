# Infrastructure-as-Code (terraform/)

Codifies the durable GCP **platform** for cheapsawari (AVF Pattern 5). The infra was
originally provisioned imperatively via `gcloud`; this configuration describes it so it
is reproducible, reviewable, and cost-gated.

## What Terraform manages
| Resource | What |
| :--- | :--- |
| `google_project_service.enabled` | Enabled APIs: run, firestore, cloudscheduler, cloudbuild, artifactregistry, iam, iamcredentials. |
| `google_firestore_database.default` | Firestore `(default)`, Native, `us-central1`. |
| `google_project_iam_member.runtime_datastore` | Runtime SA → `roles/datastore.user`. |
| `google_cloud_run_v2_service_iam_member.public_invoker` | `allUsers` → `roles/run.invoker` (the `--allow-unauthenticated`; the app does its own Google-auth gate). |
| `google_cloud_scheduler_job.daily_poll` | `POST /api/v1/poll` daily 08:00 America/Detroit, `X-Poll-Token` header. |

## What it does NOT manage (by design)
The **Cloud Run service + its revisions/image/env** stay with the app pipeline —
`gcloud run deploy --source .` (Cloud Build). Terraform reads the service as a *data
source* (`data.google_cloud_run_v2_service.api`) only to wire the scheduler URL. This
keeps infra and app deploys from fighting over the same resource. App secrets
(`POLL_TOKEN`, `TRAVELPAYOUTS_TOKEN`, `SESSION_SECRET`, `GOOGLE_CLIENT_ID`) remain Cloud
Run env vars; moving them to Secret Manager is optional future hardening.

## Files
`versions.tf` (provider + backend) · `variables.tf` · `main.tf` · `outputs.tf` ·
`terraform.tfvars.example` (copy → `terraform.tfvars`, gitignored) · `import.sh`.

## Usage — the infra already exists, so IMPORT (don't recreate)
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # set poll_token (gitignored)
terraform init
bash import.sh                                  # adopt the live resources into state
terraform plan                                  # goal: "No changes."
```
Running `apply`/`plan` *before* importing would try to recreate live resources — always
import first. After import, `terraform plan` reporting **No changes** is the proof the
code matches reality.

## Cost (Pattern 5 cost gate)
**~$0/month** at personal scale, unchanged by this codification (it describes existing
infra, provisions nothing new):
- **Cloud Run** — scales to zero; within the always-free tier at one daily poll + light UI use.
- **Firestore** — free tier (1 GiB, 50k reads / 20k writes per day) covers a handful of watches.
- **Cloud Scheduler** — 3 free jobs/month; we use 1.
- **Artifact Registry / Cloud Build** — source-deploy images are small; within free limits.
- **Travelpayouts fares** — free (affiliate-token, no per-call charge).

## Gated deployment process
1. Update these configs for any infra-dependent change.
2. `terraform plan`, confirm the diff, and check the cost note above.
3. Finalize cost + infra review before any GitHub release tag.
