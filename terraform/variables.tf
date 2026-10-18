variable "project_id" {
  description = "Shared hub project. Firebase is already enabled there (family-atlas owns that link)."
  type        = string
  default     = "mananutils"
}

variable "region" {
  description = "Region for Cloud Run, Artifact Registry, Firestore and Cloud Scheduler."
  type        = string
  default     = "us-central1"
}

variable "database_id" {
  description = "Named Firestore database. (default) belongs to family-atlas."
  type        = string
  default     = "cheapsawari"
}

variable "hosting_site_id" {
  description = "Firebase Hosting site; served at https://<id>.web.app. Globally unique."
  type        = string
  default     = "cheapsawari-mananutils"
}

variable "github_repo" {
  description = "owner/repo allowed to deploy through the shared WIF pool."
  type        = string
  default     = "mananpatel2491/cheapsawari"
}

variable "wif_pool_id" {
  description = "Shared Workload Identity pool (managed in mananutils-platform)."
  type        = string
  default     = "github"
}

variable "google_client_id" {
  description = "OAuth Web client ID for Google sign-in (public). Created by hand in the mananutils project; see terraform/README.md."
  type        = string
}

variable "admin_email" {
  description = "Bootstrap owner (ADMIN_EMAIL): always allowed; manages the allowlist."
  type        = string
  default     = "mpatel.mi24@gmail.com"
}

variable "max_instances" {
  description = "Cloud Run max instances; bounds worst-case cost."
  type        = number
  default     = 2
}

variable "scheduler_schedule" {
  description = "Cron schedule for the daily poll."
  type        = string
  default     = "0 8 * * *"
}

variable "scheduler_timezone" {
  description = "Time zone for the daily poll."
  type        = string
  default     = "America/Detroit"
}

variable "plain_env" {
  description = "Non-secret Cloud Run env vars (as deployed in the old project, plus FIRESTORE_DATABASE)."
  type        = map(string)
  default = {
    FARE_PROVIDER          = "travelpayouts"
    TRAVELPAYOUTS_CURRENCY = "usd"
    WATCH_STORE            = "firestore"
    ALERT_CHANNEL          = "email"
    SMTP_HOST              = "smtp.gmail.com"
    SMTP_PORT              = "587"
    SMTP_USER              = "mpatel.mi24@gmail.com"
    ALERT_EMAIL_FROM       = "cheapsawari (no-reply) <mpatel.mi24@gmail.com>"
    AUTH_MODE              = "google"
  }
}

variable "extra_env" {
  description = "Any other non-secret env vars found on the old service (merged over plain_env)."
  type        = map(string)
  default     = {}
}
