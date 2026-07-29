# Variables for GKE Cluster Module

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "momento-v5-cluster"
}

variable "region" {
  description = "Region for the cluster"
  type        = string
  default     = "us-central1"
}

variable "zones" {
  description = "Zones configuration with CIDR ranges"
  type = map(object({
    cidr = string
    secondary_ranges = map(object({
      range_name    = string
      ip_cidr_range = string
    }))
  }))
  default = {
    us-central1-a = {
      cidr = "10.1.0.0/24"
      secondary_ranges = {
        pods     = { range_name = "pods", ip_cidr_range = "10.2.0.0/16" }
        services = { range_name = "services", ip_cidr_range = "10.3.0.0/16" }
      }
    }
    us-central1-b = {
      cidr = "10.1.1.0/24"
      secondary_ranges = {
        pods     = { range_name = "pods", ip_cidr_range = "10.2.0.0/16" }
        services = { range_name = "services", ip_cidr_range = "10.3.0.0/16" }
      }
    }
    us-central1-c = {
      cidr = "10.1.2.0/24"
      secondary_ranges = {
        pods     = { range_name = "pods", ip_cidr_range = "10.2.0.0/16" }
        services = { range_name = "services", ip_cidr_range = "10.3.0.0/16" }
      }
    }
  }
}

variable "zones_list" {
  description = "List of zones for multi-zone deployment"
  type        = list(string)
  default     = ["us-central1-a", "us-central1-b", "us-central1-c"]
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master nodes"
  type        = string
  default     = "172.16.0.0/28"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "service_account_email" {
  description = "Service account email for GKE nodes"
  type        = string
  default     = ""
}

variable "security_group_id" {
  description = "Security group ID for authentication"
  type        = string
  default     = ""
}

variable "kms_key_name" {
  description = "KMS key name for database encryption"
  type        = string
  default     = ""
}

variable "bigquery_dataset_id" {
  description = "BigQuery dataset ID for resource usage export"
  type        = string
  default     = "momento_v5_metrics"
}

variable "authorized_networks" {
  description = "Authorized networks for cluster access"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = [
    {
      cidr_block   = "10.0.0.0/8"
      display_name = "Internal Network"
    }
  ]
}