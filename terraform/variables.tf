variable "project_id" {
  description = "GCP project id."
  type        = string
  default     = "cheapsawari"
}

variable "project_number" {
  description = "GCP project number (used for the default compute service account)."
  type        = string
  default     = "444653658968"
}

variable "region" {
  description = "Region for Cloud Run + Cloud Scheduler."
  type        = string
  default     = "us-central1"
}

variable "firestore_location" {
  description = "Firestore (default) database location. Matches the live DB; adjust if it is a multi-region (e.g. nam5)."
  type        = string
  default     = "us-central1"
}

variable "run_service_name" {
  description = "Cloud Run service name (deployed via `gcloud run deploy --source`; read here as a data source)."
  type        = string
  default     = "cheapsawari-api"
}

variable "runtime_service_account_email" {
  description = "Service account the Cloud Run service runs as (granted Firestore access)."
  type        = string
  default     = "444653658968-compute@developer.gserviceaccount.com"
}

variable "scheduler_schedule" {
  description = "Cron schedule for the daily poll job."
  type        = string
  default     = "0 8 * * *"
}

variable "scheduler_timezone" {
  description = "Time zone for the daily poll schedule."
  type        = string
  default     = "America/Detroit"
}

variable "poll_token" {
  description = "Shared secret sent as the X-Poll-Token header on the scheduler call (matches POLL_TOKEN on the service). Supply via TF_VAR_poll_token or a gitignored terraform.tfvars — never commit it."
  type        = string
  sensitive   = true
}
