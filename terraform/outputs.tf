output "app_url" {
  description = "The address to share and to add as an OAuth JavaScript origin."
  value       = "https://${google_firebase_hosting_site.app.site_id}.web.app"
}

output "service_url" {
  description = "Cloud Run's own URL (also add it as an OAuth JavaScript origin)."
  value       = google_cloud_run_v2_service.app.uri
}

output "image_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}/cheapsawari"
}

# Set these as GitHub repository *variables* (none are secret).
output "github_variables" {
  value = {
    GCP_PROJECT_ID   = var.project_id
    GCP_REGION       = var.region
    GCP_WIF_PROVIDER = "${local.wif_pool_name}/providers/github-oidc"
    GCP_DEPLOY_SA    = google_service_account.deploy.email
  }
}
