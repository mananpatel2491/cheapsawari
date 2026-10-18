# Infrastructure-as-Code (terraform/)

cheapsawari's slice of the shared GCP project **`mananutils`** (spec 008; AVF Pattern 5).
Shared pieces (the Terraform state bucket, the GitHub login gate, the account-wide budget) live in
[mananutils-platform](https://github.com/mananpatel2491/mananutils-platform). State:
`gs://mananutils-tfstate-2491/cheapsawari`.

## What Terraform manages
| Resource | What |
| :--- | :--- |
| APIs | run, firestore, cloudscheduler, artifactregistry, secretmanager, iam, iamcredentials, sts, firebase, firebasehosting |
| Firestore `cheapsawari` | Named database (Native, us-central1), delete-protected, never deleted by `destroy`. `(default)` belongs to family-atlas. |
| Artifact Registry `cheapsawari` | Images; keeps the newest 3 (free tier). |
| Secrets | `CHEAPSAWARI_POLL_TOKEN`, `_TRAVELPAYOUTS_TOKEN`, `_SESSION_SECRET`, `_SMTP_PASSWORD`: containers only, values added with gcloud. |
| SA `cheapsawari-runtime` | Cloud Run identity: Firestore user **on its own database only** (IAM condition) + its 4 secrets. |
| SA `cheapsawari-deploy` | CI identity: deploy this service, push images, act as the runtime SA. Usable only by `v*` tags of `mananpatel2491/cheapsawari` through the shared pool. |
| Cloud Run `cheapsawari-api` | Scale 0–2, 512 MiB, public (the app does its own Google sign-in + allowlist). Env and secrets come from here; GitHub Actions only swaps the image. |
| Cloud Scheduler `cheapsawari-daily-poll` | `POST /api/v1/poll` daily 08:00 America/Detroit with `X-Poll-Token`. |
| Hosting site `cheapsawari-mananutils` | `https://cheapsawari-mananutils.web.app`; Terraform-managed release forwards `**` to Cloud Run. |

**Note:** the scheduler reads the poll token from Secret Manager, so the token is in Terraform
state (private, versioned bucket, public access blocked), as it was in the old local state.

## Gate
1. `terraform fmt -check && terraform validate`
2. `terraform plan`, read it, estimate cost: ~$0/month at personal scale (scale-to-zero Cloud Run,
   one free Scheduler job, images under 0.5 GB). The named Firestore database is probably outside
   the free quota (expect cents/month; unverified).
3. Only then tag a release (tags deploy).

## One-time move from project `cheapsawari` (2026-10)
Run in Cloud Shell from the merged `main`. Old service: `cheapsawari-api` in project `cheapsawari`.

1. **Secrets first** (the service and scheduler need values before they can be created):
   ```bash
   cd terraform && cp terraform.tfvars.example terraform.tfvars   # fill google_client_id after step 2
   terraform init
   terraform apply -target='google_secret_manager_secret.app' -var google_client_id=pending
   # copy each value from the old service's env into its new secret
   OLD=$(gcloud run services describe cheapsawari-api --region us-central1 --project cheapsawari --format=json)
   for k in POLL_TOKEN TRAVELPAYOUTS_TOKEN SESSION_SECRET SMTP_PASSWORD; do
     echo "$OLD" | python3 -c "import json,sys;e={x['name']:x.get('value','') for x in json.load(sys.stdin)['spec']['template']['spec']['containers'][0]['env']};sys.stdout.write(e['$k'])" \
       | gcloud secrets versions add "CHEAPSAWARI_$k" --data-file=- --project mananutils
   done
   # list the old env NAMES so nothing is missed (values not printed)
   echo "$OLD" | python3 -c "import json,sys;print(sorted(x['name'] for x in json.load(sys.stdin)['spec']['template']['spec']['containers'][0]['env']))"
   ```
   Any name not in `plain_env`, `secret_env` or set by Terraform (`FIRESTORE_DATABASE`,
   `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLIENT_ID`, `ADMIN_EMAIL`) goes into `extra_env` in tfvars.
2. **OAuth client** (console, by hand: Google has no Terraform resource for it): mananutils →
   APIs & Services → Credentials → Create OAuth client ID → Web → name `cheapsawari`. Authorized
   JavaScript origins: `https://cheapsawari-mananutils.web.app`,
   `https://cheapsawari-mananutils.firebaseapp.com`, `http://127.0.0.1:8050`. Put the client ID in
   `terraform.tfvars`. After step 3, add the Cloud Run URL (`terraform output service_url`) too.
   Also consider renaming the OAuth consent screen (shared by every app in the project) to a
   neutral name such as "Manan Utils".
3. **Everything else**: `terraform plan` (creates only) → `terraform apply`. The service starts on a
   placeholder image.
4. **Data**: export old `(default)` → import into `cheapsawari`:
   ```bash
   ARCH=gs://mananutils-archive-2491
   ON=$(gcloud projects describe cheapsawari --format="value(projectNumber)")
   gcloud storage buckets add-iam-policy-binding $ARCH --role=roles/storage.admin \
     --member="serviceAccount:service-$ON@gcp-sa-firestore.iam.gserviceaccount.com"
   gcloud firestore export $ARCH/cheapsawari --project=cheapsawari
   gcloud firestore import $ARCH/cheapsawari --database=cheapsawari --project=mananutils
   ```
5. **GitHub variables** from `terraform output github_variables`, then tag `vX.Y.Z` on `main`:
   ```bash
   for kv in $(terraform output -json github_variables | python3 -c "import json,sys;[print(f'{k}={v}') for k,v in json.load(sys.stdin).items()]"); do
     gh variable set "${kv%%=*}" --repo mananpatel2491/cheapsawari --body "${kv#*=}"
   done
   ```
6. **Verify** (sign-in, watches present, poll works), then **pause** the old scheduler job
   (`gcloud scheduler jobs pause cheapsawari-daily-poll --location us-central1 --project cheapsawari`)
   so two polls don't run, and delete project `cheapsawari` once happy.
