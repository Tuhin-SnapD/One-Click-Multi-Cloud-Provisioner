# Output definitions for GCP infrastructure

output "vpc_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.main.id
}

output "vpc_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.main.name
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = google_compute_subnetwork.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = google_compute_subnetwork.private[*].id
}

output "instance_ips" {
  description = "External IP addresses of VM instances"
  value       = google_compute_instance.app[*].network_interface[0].access_config[0].nat_ip
}

output "instance_internal_ips" {
  description = "Internal IP addresses of VM instances"
  value       = google_compute_instance.app[*].network_interface[0].network_ip
}

output "instance_ids" {
  description = "IDs of VM instances"
  value       = google_compute_instance.app[*].id
}

output "cloudsql_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = var.enable_db ? google_sql_database_instance.main[0].connection_name : null
}

output "cloudsql_private_ip" {
  description = "Cloud SQL instance private IP"
  value       = var.enable_db ? google_sql_database_instance.main[0].private_ip_address : null
}

