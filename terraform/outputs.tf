output "run_service_url" {
  description = "Public URL of the Cloud Run service."
  value       = data.google_cloud_run_v2_service.api.uri
}

output "firestore_database" {
  description = "Firestore database name + location."
  value       = "${google_firestore_database.default.name} (${google_firestore_database.default.location_id}, ${google_firestore_database.default.type})"
}

output "scheduler_job" {
  description = "Daily poll job + schedule."
  value       = "${google_cloud_scheduler_job.daily_poll.name} @ '${google_cloud_scheduler_job.daily_poll.schedule}' ${google_cloud_scheduler_job.daily_poll.time_zone}"
}

output "enabled_services" {
  description = "APIs managed by Terraform."
  value       = sort([for s in google_project_service.enabled : s.service])
}
