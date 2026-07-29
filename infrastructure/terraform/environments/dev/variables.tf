# Variables for Momento Core V5 - Development Environment

variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "momento-core-dev"
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zones" {
  description = "GCP zones configuration"
  type = map(object({
    cidr = string
    secondary_ranges = map(object({
      range_name    = string
      ip_cidr_range = string
    }))
  }))
  default = {
    "us-central1-a" = {
      cidr = "10.0.1.0/24"
      secondary_ranges = {
        pods     = { range_name = "pods", ip_cidr_range = "10.1.0.0/16" }
        services = { range_name = "services", ip_cidr_range = "10.2.0.0/16" }
      }
    }
    "us-central1-b" = {
      cidr = "10.0.2.0/24"
      secondary_ranges = {
        pods     = { range_name = "pods", ip_cidr_range = "10.1.0.0/16" }
        services = { range_name = "services", ip_cidr_range = "10.2.0.0/16" }
      }
    }
    "us-central1-c" = {
      cidr = "10.0.3.0/24"
      secondary_ranges = {
        pods     = { range_name = "pods", ip_cidr_range = "10.1.0.0/16" }
        services = { range_name = "services", ip_cidr_range = "10.2.0.0/16" }
      }
    }
  }
}

variable "zones_list" {
  description = "List of GCP zones"
  type        = list(string)
  default     = ["us-central1-a", "us-central1-b", "us-central1-c"]
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master"
  type        = string
  default     = "172.16.0.0/28"
}

variable "service_account_email" {
  description = "Service account email for GKE nodes"
  type        = string
  default     = "momento-core-sa@momento-core-dev.iam.gserviceaccount.com"
}

variable "security_group_id" {
  description = "Security group ID for GKE authentication"
  type        = string
  default     = ""
}

variable "authorized_networks" {
  description = "Authorized networks for GKE API access"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = [
    {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks (dev only)"
    }
  ]
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset ID for resource usage export"
  type        = string
  default     = "momento_core_usage"
}

variable "kms_key_name" {
  description = "KMS key name for encryption"
  type        = string
  default     = "projects/momento-core-dev/locations/us-central1/keyRings/momento-core/cryptoKeys/momento-core-key"
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "github_org" {
  description = "GitHub organization"
  type        = string
  default     = "momento-core"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}
