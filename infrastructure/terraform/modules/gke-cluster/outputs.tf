# Outputs for GKE Cluster Module

output "cluster_endpoint" {
  description = "Cluster endpoint"
  value       = google_container_cluster.primary.endpoint
}

output "cluster_ca_certificate" {
  description = "Cluster CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
}

output "cluster_name" {
  description = "Cluster name"
  value       = google_container_cluster.primary.name
}

output "location" {
  description = "Cluster location"
  value       = google_container_cluster.primary.location
}

output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "subnetwork_names" {
  description = "Subnetwork names"
  value       = [for subnet in google_compute_subnetwork.subnet : subnet.name]
}

output "node_service_account_email" {
  description = "Node service account email"
  value       = google_service_account.nodes.email
}

output "kubernetes_version" {
  description = "Kubernetes version"
  value       = google_container_cluster.primary.master_version
}

output "node_pool_names" {
  description = "Node pool names"
  value       = { for k, v in google_container_node_pool.node_pools : k => v.name }
}