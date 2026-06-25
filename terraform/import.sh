#!/usr/bin/env bash
# Adopt the EXISTING (gcloud-provisioned) cheapsawari infra into Terraform state.
# Run once, from terraform/, after `terraform init` and with terraform.tfvars in place.
# After it completes, `terraform plan` should show no changes (the goal of Pattern 5).
set -euo pipefail

PROJECT="cheapsawari"
REGION="us-central1"
SA="444653658968-compute@developer.gserviceaccount.com"
SERVICE="cheapsawari-api"

# Enabled APIs (one import per for_each key).
for api in run.googleapis.com firestore.googleapis.com cloudscheduler.googleapis.com \
           cloudbuild.googleapis.com artifactregistry.googleapis.com \
           iam.googleapis.com iamcredentials.googleapis.com; do
  terraform import "google_project_service.enabled[\"${api}\"]" "${PROJECT}/${api}"
done

# Firestore (default) database.
terraform import google_firestore_database.default "projects/${PROJECT}/databases/(default)"

# Runtime SA -> roles/datastore.user.
terraform import google_project_iam_member.runtime_datastore \
  "${PROJECT} roles/datastore.user serviceAccount:${SA}"

# Public invoker (allow-unauthenticated) on the Cloud Run service.
terraform import google_cloud_run_v2_service_iam_member.public_invoker \
  "projects/${PROJECT}/locations/${REGION}/services/${SERVICE} roles/run.invoker allUsers"

# Daily poll scheduler job.
terraform import google_cloud_scheduler_job.daily_poll \
  "projects/${PROJECT}/locations/${REGION}/jobs/cheapsawari-daily-poll"

echo
echo "Imports done. Now run: terraform plan   (expect: No changes.)"
