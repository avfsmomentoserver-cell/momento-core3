# V5 Multi-Region Enterprise Deployment
# Terraform configuration for multi-region Kubernetes deployment

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
  
  backend "gcs" {
    bucket = "momento-v5-terraform-state"
    prefix = "multi-region"
  }
}

provider "google" {
  project = var.project_id
  region  = var.primary_region
}

provider "kubernetes" {
  host                   = module.gke_primary.endpoint
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.gke_primary.ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = module.gke_primary.endpoint
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(module.gke_primary.ca_certificate)
  }
}

# Data sources
data "google_client_config" "default" {}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "primary_region" {
  description = "Primary region for deployment"
  type        = string
  default     = "us-central1"
}

variable "secondary_region" {
  description = "Secondary region for DR"
  type        = string
  default     = "us-east1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# VPC Network
module "vpc_network" {
  source       = "./modules/vpc"
  project_id   = var.project_id
  primary_region   = var.primary_region
  secondary_region = var.secondary_region
  environment  = var.environment
}

# Primary GKE Cluster
module "gke_primary" {
  source      = "./modules/gke"
  project_id  = var.project_id
  region      = var.primary_region
  network     = module.vpc_network.network_name
  subnet      = module.vpc_network.primary_subnet
  environment = var.environment
  cluster_name = "momento-v5-primary"
  
  node_pools = {
    general = {
      machine_type = "n2-standard-4"
      node_count   = 3
      autoscaling  = {
        min       = 3
        max       = 10
      }
    }
    gpu = {
      machine_type = "n1-standard-8"
      accelerator_type = "nvidia-tesla-t4"
      node_count   = 2
      autoscaling  = {
        min       = 2
        max       = 5
      }
    }
    highmem = {
      machine_type = "n2-highmem-8"
      node_count   = 2
      autoscaling  = {
        min       = 2
        max       = 6
      }
    }
  }
}

# Secondary GKE Cluster (DR)
module "gke_secondary" {
  source      = "./modules/gke"
  project_id  = var.project_id
  region      = var.secondary_region
  network     = module.vpc_network.network_name
  subnet      = module.vpc_network.secondary_subnet
  environment = var.environment
  cluster_name = "momento-v5-secondary"
  
  node_pools = {
    general = {
      machine_type = "n2-standard-4"
      node_count   = 2
      autoscaling  = {
        min       = 2
        max       = 8
      }
    }
  }
}

# Cloud SQL (PostgreSQL)
module "cloud_sql" {
  source      = "./modules/cloudsql"
  project_id  = var.project_id
  region      = var.primary_region
  network     = module.vpc_network.network_name
  environment = var.environment
  
  database_version = "POSTGRES_15"
  tier            = "db-custom-8-32"
  availability_type = "REGIONAL"
  
  backup_configuration = {
    enabled            = true
    start_time         = "03:00"
    location           = var.secondary_region
    point_in_time_recovery_enabled = true
  }
}

# Memorystore (Redis)
module "memorystore" {
  source      = "./modules/memorystore"
  project_id  = var.project_id
  region      = var.primary_region
  network     = module.vpc_network.network_name
  environment = var.environment
  
  tier = "STANDARD_HA"
  memory_size_gb = 16
  redis_version = "7.2"
  
  maintenance_policy = {
    day = "SUNDAY"
    start_time = "03:00"
  }
}

# Load Balancer
module "load_balancer" {
  source      = "./modules/loadbalancer"
  project_id  = var.project_id
  network     = module.vpc_network.network_name
  environment = var.environment
  
  backend_services = {
    primary = {
      name       = "momento-backend-primary"
      port       = 80
      protocol   = "HTTP"
      backends   = [module.gke_primary.endpoint]
      health_check = {
        port = 80
        path = "/health"
      }
    }
    secondary = {
      name       = "momento-backend-secondary"
      port       = 80
      protocol   = "HTTP"
      backends   = [module.gke_secondary.endpoint]
      health_check = {
        port = 80
        path = "/health"
      }
    }
  }
}

# Cloud Armor for DDoS protection
module "cloud_armor" {
  source      = "./modules/cloudarmor"
  project_id  = var.project_id
  environment = var.environment
  
  security_policy = {
    name = "momento-v5-security"
    rules = [
      {
        action        = "allow"
        priority      = 1000
        match = {
          expr = "evaluatePreconfiguredExpr('ddos_v4_protection')"
        }
      }
    ]
  }
}

# Monitoring and Alerting
module "monitoring" {
  source      = "./modules/monitoring"
  project_id  = var.project_id
  environment = var.environment
  
  notification_channels = {
    email = ["ops@momento.local"]
    pagerduty = ["momento-pagerduty"]
  }
  
  alert_policies = {
    high_error_rate = {
      conditions = [
        {
          display_name = "High Error Rate"
          condition = {
            type = "log_match"
            filter = 'severity="ERROR"'
          }
        }
      ]
    }
    high_latency = {
      conditions = [
        {
          display_name = "High Latency"
          condition = {
            type = "metric_threshold"
            metric = "latency"
            threshold = 1000
          }
        }
      ]
    }
  }
}

# Outputs
output "primary_cluster_endpoint" {
  value = module.gke_primary.endpoint
}

output "secondary_cluster_endpoint" {
  value = module.gke_secondary.endpoint
}

output "database_connection" {
  value     = module.cloud_sql.connection_string
  sensitive = true
}

output "redis_connection" {
  value     = module.memorystore.connection_string
  sensitive = true
}

output "load_balancer_ip" {
  value = module.load_balancer.external_ip
}