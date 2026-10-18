# cheapsawari's slice of the shared GCP project `mananutils` (spec 008, AVF Pattern 5).
# Shared pieces (state bucket, GitHub login gate, budget) live in mananpatel2491/mananutils-platform.
#
# Terraform owns the whole service: APIs, named Firestore database, image registry, secrets
# (containers only; values are added with gcloud so they never come from git), identities,
# the Cloud Run service (env + secrets; GitHub Actions only swaps the image), public access,
# the daily poll, and the Firebase Hosting front door.

locals {
  service = "cheapsawari-api"
  apis = [
    "run.googleapis.com",
    "firestore.googleapis.com",
    "cloudscheduler.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
  ]
  # Secret env var -> Secret Manager secret id. Values are copied from the old service (see README).
  secret_env = {
    POLL_TOKEN          = "CHEAPSAWARI_POLL_TOKEN"
    TRAVELPAYOUTS_TOKEN = "CHEAPSAWARI_TRAVELPAYOUTS_TOKEN"
    SESSION_SECRET      = "CHEAPSAWARI_SESSION_SECRET"
    SMTP_PASSWORD       = "CHEAPSAWARI_SMTP_PASSWORD"
  }
  plain_env = merge(var.plain_env, var.extra_env, {
    FIRESTORE_DATABASE   = var.database_id
    GOOGLE_CLOUD_PROJECT = var.project_id
    GOOGLE_CLIENT_ID     = var.google_client_id
    ADMIN_EMAIL          = var.admin_email
  })
  wif_pool_name = "projects/${data.google_project.this.number}/locations/global/workloadIdentityPools/${var.wif_pool_id}"
}

data "google_project" "this" {}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false # shared project: other apps use these
}

# --- data ----------------------------------------------------------------------------------------

resource "google_firestore_database" "app" {
  name                    = var.database_id
  location_id             = var.region
  type                    = "FIRESTORE_NATIVE"
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  deletion_policy         = "ABANDON" # `terraform destroy` never deletes watch data
  depends_on              = [google_project_service.apis]
}

# --- images --------------------------------------------------------------------------------------

resource "google_artifact_registry_repository" "app" {
  repository_id = "cheapsawari"
  location      = var.region
  format        = "DOCKER"
  description   = "cheapsawari images"

  # Stay inside the 0.5 GB free storage: keep the 3 newest images.
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }
  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "86400s"
    }
  }
  depends_on = [google_project_service.apis]
}

# --- secrets (containers only) -------------------------------------------------------------------

resource "google_secret_manager_secret" "app" {
  for_each  = local.secret_env
  secret_id = each.value
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# The scheduler must send the same token the service checks. Reading it here puts the token in
# Terraform state (private, versioned bucket with public access blocked), as the old config did.
data "google_secret_manager_secret_version" "poll_token" {
  secret = google_secret_manager_secret.app["POLL_TOKEN"].secret_id
}

# --- identities ----------------------------------------------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "cheapsawari-runtime"
  display_name = "cheapsawari Cloud Run runtime"
}

# Firestore access limited to this app's own database (the project hosts other apps' data).
resource "google_project_iam_member" "runtime_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"
  condition {
    title      = "cheapsawari-db-only"
    expression = "resource.name == \"projects/${var.project_id}/databases/${var.database_id}\""
  }
}

resource "google_secret_manager_secret_iam_member" "runtime_secret" {
  for_each  = google_secret_manager_secret.app
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_service_account" "deploy" {
  account_id   = "cheapsawari-deploy"
  display_name = "cheapsawari GitHub deploys"
}

resource "google_cloud_run_v2_service_iam_member" "deploy_run" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_artifact_registry_repository_iam_member" "deploy_push" {
  repository = google_artifact_registry_repository.app.name
  location   = var.region
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_service_account_iam_member" "deploy_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

# Only this repository's v* tags (gate in mananutils-platform) may act as the deploy SA.
resource "google_service_account_iam_member" "deploy_wif" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${local.wif_pool_name}/attribute.repository/${var.github_repo}"
}

# --- the service ---------------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "app" {
  name                = local.service
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account                  = google_service_account.runtime.email
    max_instance_request_concurrency = 80
    timeout                          = "60s"
    scaling {
      min_instance_count = 0 # scale to zero: $0 when idle
      max_instance_count = var.max_instances
    }
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # replaced by the first tag deploy
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      dynamic "env" {
        for_each = local.plain_env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.app[env.key].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version, scaling]
  }
  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_member.runtime_secret,
    google_project_iam_member.runtime_firestore,
  ]
}

# Public; the app does its own Google sign-in + allowlist gate.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- daily poll ----------------------------------------------------------------------------------

resource "google_cloud_scheduler_job" "daily_poll" {
  name      = "cheapsawari-daily-poll"
  region    = var.region
  schedule  = var.scheduler_schedule
  time_zone = var.scheduler_timezone

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.app.uri}/api/v1/poll"
    body        = base64encode("{}")
    headers = {
      "Content-Type" = "application/json"
      "X-Poll-Token" = data.google_secret_manager_secret_version.poll_token.secret_data
    }
  }
  depends_on = [google_project_service.apis]
}

# --- front door: Firebase Hosting -> Cloud Run ---------------------------------------------------

resource "google_firebase_hosting_site" "app" {
  provider   = google-beta
  site_id    = var.hosting_site_id
  depends_on = [google_project_service.apis]
}

resource "google_firebase_hosting_version" "app" {
  provider = google-beta
  site_id  = google_firebase_hosting_site.app.site_id
  config {
    rewrites {
      glob = "**"
      run {
        service_id = google_cloud_run_v2_service.app.name
        region     = var.region
      }
    }
  }
}

resource "google_firebase_hosting_release" "app" {
  provider     = google-beta
  site_id      = google_firebase_hosting_site.app.site_id
  version_name = google_firebase_hosting_version.app.name
  message      = "Forward all traffic to Cloud Run (managed by Terraform)"
}
