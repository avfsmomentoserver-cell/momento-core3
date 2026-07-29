# GKE Cluster Module for V5 Infrastructure
# This module creates a production-ready Google Kubernetes Engine cluster
# with multi-zone configuration and autoscaling capabilities

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.80.0"
    }
  }
}

locals {
  # Node pool configurations based on V5 specifications
  node_pools = {
    default = {
      machine_type    = "n2-highmem-32"
      node_count      = 3
      autoscaling_min = 3
      autoscaling_max = 10
      disk_size_gb    = 100
      disk_type       = "pd-ssd"
      labels = {
        role = "default"
        tier = "standard"
      }
      taints = []
    }
    
    gpu = {
      machine_type    = "n2-highmem-32"
      node_count      = 2
      autoscaling_min = 2
      autoscaling_max = 5
      disk_size_gb    = 200
      disk_type       = "pd-ssd"
      labels = {
        role = "gpu"
        tier = "accelerated"
      }
      taints = [
        {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]
      accelerator_type = "nvidia-tesla-a100"
      accelerator_count = 2
    }
    
    critical = {
      machine_type    = "n2-highmem-32"
      node_count      = 3
      autoscaling_min = 3
      autoscaling_max = 6
      disk_size_gb    = 100
      disk_type       = "pd-ssd"
      labels = {
        role = "critical"
        tier = "high-availability"
      }
      taints = [
        {
          key    = "workload"
          value  = "critical"
          effect = "PREFER_NO_SCHEDULE"
        }
      ]
    }
  }
}

# Create VPC network
resource "google_compute_network" "vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
  description             = "VPC network for ${var.cluster_name} cluster"
  routing_mode            = "REGIONAL"
}

# Create subnets for each zone
resource "google_compute_subnetwork" "subnet" {
  for_each = var.zones

  name          = "${var.cluster_name}-subnet-${each.key}"
  ip_cidr_range = each.value.cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  
  private_ip_google_access = true
  
  dynamic "secondary_ip_range" {
    for_each = each.value.secondary_ranges
    content {
      range_name    = secondary_ip_range.value.range_name
      ip_cidr_range = secondary_ip_range.value.ip_cidr_range
    }
  }
  
  logs_flow_enabled    = true
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Create Cloud Router for NAT
resource "google_compute_router" "router" {
  name    = "${var.cluster_name}-router"
  region  = var.region
  network = google_compute_network.vpc.id
  
  bgp {
    asn = 65001
  }
}

# Create Cloud NAT for private clusters
resource "google_compute_router_nat" "nat" {
  name                               = "${var.cluster_name}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# GKE Cluster
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  
  # V5 Specification: 6+ nodes, multi-zone
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.vpc.name
  subnetwork = values(google_compute_subnetwork.subnet)[0].name
  
  # Private cluster configuration for security
  private_cluster_config {
    enable_private_endpoint = true
    enable_private_nodes    = true
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block
  }
  
  # Release channel for automatic upgrades
  release_channel {
    channel = "RAPID"
  }
  
  # V5 Specification: Kubernetes 1.28+
  min_master_version = "1.28"
  
  # Network policy
  network_policy {
    enabled  = true
    provider = "CALICO"
  }
  
  # Add-on configurations
  addons_config {
    http_load_balancing {
      enabled = true
    }
    
    horizontal_pod_autoscaling {
      enabled = true
    }
    
    network_policy_config {
      enabled = true
    }
    
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
    
    config_connector_config {
      enabled = false
    }
    
    dns_cache_config {
      enabled = true
    }
  }
  
  # Maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
  
  # Resource usage export
  resource_usage_export_config {
    enable_network_egress_metering = true
    enable_resource_consumption_metering = true
    
    bigquery_destination {
      dataset_id = var.bigquery_dataset_id
    }
  }
  
  # Authentication
  authenticator_groups_config {
    security_group = var.security_group_id
  }
  
  # Binary authorization
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }
  
  # Database encryption
  database_encryption {
    state    = "ENCRYPTED"
    key_name = var.kms_key_name
  }
  
  # Workload identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Logging and monitoring
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
  
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
  }
  
  # Master authorized networks
  master_authorized_networks_config {
    dynamic "cidr_blocks" {
      for_each = var.authorized_networks
      content {
        cidr_block   = cidr_blocks.value.cidr_block
        display_name = cidr_blocks.value.display_name
      }
    }
  }
  
  # Cluster autoscaling
  cluster_autoscaling {
    enabled = true
    auto_provisioning_defaults {
      oauth_scopes = [
        "https://www.googleapis.com/auth/logging.write",
        "https://www.googleapis.com/auth/monitoring",
        "https://www.googleapis.com/auth/devstorage.read_only",
      ]
      
      service_account = var.service_account_email
      
      upgrade_settings {
        max_surge       = 1
        max_unavailable = 0
      }
    }
    
    resource_limits {
      resource_type = "cpu"
      maximum       = 256
    }
    
    resource_limits {
      resource_type = "memory"
      maximum       = 1024
    }
  }
  
  # Node locations (multi-zone)
  node_locations = var.zones_list
  
  # Timeout settings
  timeout {
    create = "30m"
    update = "30m"
    delete = "30m"
  }
  
  labels = {
    environment = var.environment
    project     = "momento-core"
    version     = "v5"
  }
  
  depends_on = [
    google_compute_router_nat.nat
  ]
}

# Create node pools
resource "google_container_node_pool" "node_pools" {
  for_each = local.node_pools
  
  name     = "${var.cluster_name}-${each.key}-pool"
  location = var.region
  cluster   = google_container_cluster.primary.name
  
  node_count = each.value.node_count
  
  node_config {
    machine_type = each.value.machine_type
    
    disk_size_gb = each.value.disk_size_gb
    disk_type    = each.value.disk_type
    
    image_type = "COS_CONTAINERD"
    
    service_account = var.service_account_email
    
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    
    labels = merge(each.value.labels, {
      environment = var.environment
      project     = "momento-core"
      version     = "v5"
    })
    
    dynamic "taint" {
      for_each = each.value.taints
      content {
        key    = taint.value.key
        value  = taint.value.value
        effect = taint.value.effect
      }
    }
    
    dynamic "guest_accelerator" {
      for_each = each.value.accelerator_type != null ? [1] : []
      content {
        type  = each.value.accelerator_type
        count = each.value.accelerator_count
      }
    }
    
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
  
  autoscaling {
    min_node_count = each.value.autoscaling_min
    max_node_count = each.value.autoscaling_max
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
  
  lifecycle {
    ignore_changes = [
      node_count
    ]
  }
}

# Service account for nodes
resource "google_service_account" "nodes" {
  account_id   = "${var.cluster_name}-nodes"
  display_name = "Service account for ${var.cluster_name} nodes"
  
  depends_on = [
    google_project_iam_member.roles
  ]
}

# IAM roles for node service account
resource "google_project_iam_member" "roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceUser",
    "roles/storage.objectViewer",
    "roles/iam.serviceAccountUser",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.nodes.email}"
}

# Cluster endpoint (for private cluster access)
output "cluster_endpoint" {
  value = google_container_cluster.primary.endpoint
}

output "cluster_ca_certificate" {
  value = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
}

output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "location" {
  value = google_container_cluster.primary.location
}

output "network_name" {
  value = google_compute_network.vpc.name
}

output "subnetwork_names" {
  value = [for subnet in google_compute_subnetwork.subnet : subnet.name]
}

output "node_service_account_email" {
  value = google_service_account.nodes.email
}