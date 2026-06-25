# Provider + version pinning. State is local by default (fine for a single-owner $0
# project); to share state, switch to a GCS backend (commented below).
terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # backend "gcs" {
  #   bucket = "cheapsawari-tfstate"   # create once, then `terraform init -migrate-state`
  #   prefix = "prod"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
