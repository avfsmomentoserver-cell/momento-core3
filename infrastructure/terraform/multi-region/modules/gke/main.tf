# GKE Cluster Module for V5 Deployment

resource "google_container_cluster" "gke_cluster" {
  name     = var.cluster_name
  location = var.region
  
  network    = var.network
  subnetwork = var.subnet
  
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # V5-specific configurations
  master_authorized_networks_config {
    gcp_public_cidrs_access_enabled = true
  }
  
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }
  
  # Security configurations
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "all-networks"
    }
  }
  
  # Add-on configurations
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
    istio_config {
      disabled = false
      auth     = "AUTH_MUTUAL_TLS"
    }
  }
  
  # Network policy
  network_policy {
    enabled  = true
    provider = "CALICO"
  }
  
  # Pod security policy
  pod_security_policy_config {
    enabled = true
  }
  
  # Private cluster configuration
  private_cluster_config {
    enable_private_endpoint = true
    enable_private_nodes    = true
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }
  
  # Workload identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Database encryption
  database_encryption {
    state    = "ENCRYPTED"
    key_name = var.kms_key_name
  }
  
  # Maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
  
  # Resource labels
  resource_labels = {
    environment = var.environment
    cluster     = var.cluster_name
  }
}

# Node pools
resource "google_container_node_pool" "node_pools" {
  for_each = var.node_pools
  
  name       = "${var.cluster_name}-${each.key}"
  location   = var.region
  cluster    = google_container_cluster.gke_cluster.name
  
  node_count = each.value.node_count
  
  node_config {
    machine_type = each.value.machine_type
    
    # GPU configuration
    dynamic "guest_accelerator" {
      for_each = lookup(each.value, "accelerator_type", []) != [] ? [1] : []
      content {
        type  = each.value.accelerator_type
        count = lookup(each.value, "accelerator_count", 1)
      }
    }
    
    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    # Service account
    service_account = var.service_account_email
    
    # Labels
    labels = {
      environment = var.environment
      pool       = each.key
    }
    
    # Taints
    dynamic "taint" {
      for_each = lookup(each.value, "taints", [])
      content {
        key    = taint.key
        value  = lookup(taint, "value", "")
        effect = taint.effect
      }
    }
  }
  
  # Autoscaling
  dynamic "autoscaling" {
    for_each = lookup(each.value, "autoscaling", {}) != {} ? [1] : []
    content {
      min_node_count = each.value.autoscaling.min
      max_node_count = each.value.autoscaling.max
    }
  }
  
  # Management
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  # Upgrade settings
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "network" {
  description = "VPC network name"
  type        = string
}

variable "subnet" {
  description = "Subnet name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "cluster_name" {
  description = "Cluster name"
  type        = string
}

variable "node_pools" {
  description = "Node pool configurations"
  type = map(object({
    machine_type     = string
    node_count       = number
    accelerator_type = optional(string)
    accelerator_count = optional(number)
    autoscaling      = optional(map(number))
    taints           = optional(list(map(string)))
  }))
}

variable "service_account_email" {
  description = "Service account email for nodes"
  type        = string
  default     = ""
}

variable "kms_key_name" {
  description = "KMS key name for database encryption"
  type        = string
  default     = ""
}

# Outputs
output "endpoint" {
  value = google_container_cluster.gke_cluster.endpoint
}

output "ca_certificate" {
  value = google_container_cluster.gke_cluster.master_auth[0].cluster_ca_certificate
}

output "cluster_name" {
  value = google_container_cluster.gke_cluster.name
}