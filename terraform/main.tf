# cheapsawari infrastructure-as-code (AVF Pattern 5).
#
# Scope: this codifies the durable *platform* — enabled APIs, the Firestore database,
# the runtime service account's IAM, the public-invoker binding, and the daily Cloud
# Scheduler poll. The Cloud Run *service + its revisions/image/env* are intentionally
# NOT managed here — they are deployed by `gcloud run deploy --source .` (Cloud Build),
# and read back below as a data source. This keeps app deploys and infra apart so they
# never fight over the same resource.
#
# Everything here ALREADY EXISTS (it was provisioned imperatively via gcloud). Adopt it
# into Terraform state with the commands in import.sh BEFORE running apply, or Terraform
# will try to recreate it. After importing, `terraform plan` should report no changes.

locals {
  # APIs the project depends on.
  services = [
    "run.googleapis.com",
    "firestore.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
  ]
}

# --- enabled APIs ----------------------------------------------------------
resource "google_project_service" "enabled" {
  for_each = toset(local.services)
  project  = var.project_id
  service  = each.value

  # Don't disable the API on `terraform destroy` — these underpin live resources.
  disable_on_destroy = false
}

# --- Firestore (Native) ----------------------------------------------------
resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.enabled]
}

# --- runtime service account IAM -------------------------------------------
# The Cloud Run runtime SA needs Firestore (Datastore) access for the watch store.
resource "google_project_iam_member" "runtime_datastore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.runtime_service_account_email}"
}

# --- Cloud Run service (read-only; deployed by gcloud) ---------------------
data "google_cloud_run_v2_service" "api" {
  project  = var.project_id
  location = var.region
  name     = var.run_service_name
}

# Public access (the app does its own Google-auth gate). Equivalent to
# `gcloud run deploy --allow-unauthenticated`.
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = var.run_service_name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- daily poll (Cloud Scheduler) ------------------------------------------
resource "google_cloud_scheduler_job" "daily_poll" {
  project   = var.project_id
  region    = var.region
  name      = "cheapsawari-daily-poll"
  schedule  = var.scheduler_schedule
  time_zone = var.scheduler_timezone

  http_target {
    http_method = "POST"
    uri         = "${data.google_cloud_run_v2_service.api.uri}/api/v1/poll"
    body        = base64encode("{}")
    headers = {
      "Content-Type" = "application/json"
      "X-Poll-Token" = var.poll_token
    }
  }

  depends_on = [google_project_service.enabled]
}
