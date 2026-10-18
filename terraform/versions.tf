terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.12"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.12"
    }
  }
  # Shared state bucket, created by mananpatel2491/mananutils-platform.
  backend "gcs" {
    bucket = "mananutils-tfstate-2491"
    prefix = "cheapsawari"
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

# Firebase Hosting resources live in the beta provider.
provider "google-beta" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}
