# Outputs for Momento Core V5 - Development Environment

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = module.gke-cluster.endpoint
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = module.gke-cluster.ca_certificate
  sensitive   = true
}

output "cluster_name" {
  description = "GKE cluster name"
  value       = module.gke-cluster.cluster_name
}

output "network_id" {
  description = "VPC network ID"
  value       = module.gke-cluster.network_id
}

output "subnet_ids" {
  description = "Subnet IDs"
  value       = module.gke-cluster.subnet_ids
}

output "postgres_connection_name" {
  description = "Cloud SQL connection name"
  value       = module.cloud-sql.connection_name
}

output "postgres_instance_name" {
  description = "Cloud SQL instance name"
  value       = module.cloud-sql.instance_name
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.redis.host
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.redis.port
}

output "backup_bucket" {
  description = "Cloud Storage bucket for backups"
  value       = google_storage_bucket.backups.name
}

output "istio_ingress_ip" {
  description = "Istio ingress IP"
  value       = helm_release.istio-ingress.status == "deployed" ? "LoadBalancer IP pending" : "Not deployed"
}
