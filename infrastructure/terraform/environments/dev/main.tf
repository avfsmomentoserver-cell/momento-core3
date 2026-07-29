# Terraform Configuration for Momento Core V5 - Development Environment
# V5 Specification: Infrastructure as Code for scalable deployment

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.80.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.23.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.11.0"
    }
  }

  backend "gcs" {
    bucket = "momento-core-terraform-state"
    prefix = "environments/dev"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "kubernetes" {
  host                   = module.gke-cluster.endpoint
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.gke-cluster.ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = module.gke-cluster.endpoint
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(module.gke-cluster.ca_certificate)
  }
}

data "google_client_config" "default" {}

# GKE Cluster Module
module "gke-cluster" {
  source = "../../modules/gke-cluster"

  cluster_name           = "momento-core-dev"
  project_id             = var.project_id
  region                 = var.region
  environment            = "dev"
  zones                  = var.zones
  zones_list             = var.zones_list
  master_ipv4_cidr_block = var.master_ipv4_cidr_block
  service_account_email  = var.service_account_email
  security_group_id      = var.security_group_id
  authorized_networks    = var.authorized_networks
  bigquery_dataset_id    = var.bigquery_dataset_id
  kms_key_name           = var.kms_key_name
}

# Cloud SQL for PostgreSQL
module "cloud-sql" {
  source  = "GoogleCloudPlatform/sql-db/google"
  version = "13.0.0"

  name             = "momento-core-dev"
  project_id       = var.project_id
  database_version = "POSTGRES_15"
  region           = var.region
  zone             = var.zones_list[0]

  tier              = "db-custom-2-3840"
  disk_size         = 100
  disk_type         = "pd-ssd"
  availability_type = "REGIONAL"

  deletion_protection = false

  database_flags = [
    {
      name  = "max_connections"
      value = "200"
    },
    {
      name  = "shared_buffers"
      value = "4GB"
    },
    {
      name  = "effective_cache_size"
      value = "12GB"
    }
  ]

  users = [
    {
      name     = "momento"
      password = var.postgres_password
    }
  ]

  databases = [
    {
      name = "momento"
    }
  ]

  ip_configuration = {
    ipv4_enabled    = true
    private_network = module.gke-cluster.network_id
    require_ssl    = true
  }
}

# Memorystore for Redis
resource "google_redis_instance" "redis" {
  name           = "momento-core-dev-redis"
  project        = var.project_id
  region         = var.region
  tier           = "STANDARD_HA"
  memory_size_gb = 8
  redis_version  = "7.2"

  location_id             = var.zones_list[0]
  replica_count           = 2
  display_name            = "Momento Core Dev Redis"
  authorized_network      = module.gke-cluster.network_id
  connect_mode            = "PRIVATE_SERVICE_ACCESS"
  redis_configs           = {
    maxmemory-policy = "allkeys-lru"
  }

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 2
        minutes = 0
      }
    }
  }

  labels = {
    environment = "dev"
    project     = "momento-core"
    version     = "v5"
  }
}

# Cloud Storage for backups
resource "google_storage_bucket" "backups" {
  name          = "momento-core-dev-backups"
  project       = var.project_id
  location      = var.region
  force_destroy = false
  storage_class = "NEARLINE"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true

  labels = {
    environment = "dev"
    project     = "momento-core"
    version     = "v5"
  }
}

# Helm Release for Istio
resource "helm_release" "istio-base" {
  name       = "istio-base"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "base"
  namespace  = "istio-system"
  version    = "1.19.0"

  create_namespace = true

  set {
    name  = "defaultRevision"
    value = "default"
  }
}

resource "helm_release" "istiod" {
  name       = "istiod"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "istiod"
  namespace  = "istio-system"
  version    = "1.19.0"

  depends_on = [helm_release.istio-base]

  set {
    name  = "revision"
    value = "default"
  }
}

resource "helm_release" "istio-ingress" {
  name       = "istio-ingress"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "gateway"
  namespace  = "istio-system"
  version    = "1.19.0"

  depends_on = [helm_release.istiod]

  set {
    name  = "revision"
    value = "default"
  }

  set {
    name  = "service.type"
    value = "LoadBalancer"
  }
}

# Helm Release for Monitoring Stack
resource "helm_release" "kube-prometheus-stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "monitoring"
  version    = "48.0.0"

  create_namespace = true

  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "30d"
  }

  set {
    name  = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName"
    value = "fast-ssd"
  }

  set {
    name  = "grafana.persistence.storageClassName"
    value = "fast-ssd"
  }

  set {
    name  = "grafana.persistence.size"
    value = "20Gi"
  }
}

# Helm Release for Momento Core
resource "helm_release" "momento-core" {
  name       = "momento-core"
  repository = "oci://ghcr.io/${var.github_org}/helm-charts"
  chart      = "momento-core"
  namespace  = "momento-v5"
  version    = "5.0.0"

  create_namespace = true

  set {
    name  = "image.tag"
    value = var.image_tag
  }

  set {
    name  = "postgres.host"
    value = module.cloud-sql.connection_name
  }

  set {
    name  = "redis.host"
    value = google_redis_instance.redis.host
  }

  set {
    name  = "resources.requests.memory"
    value = "512Mi"
  }

  set {
    name  = "resources.requests.cpu"
    value = "500m"
  }

  set {
    name  = "autoscaling.enabled"
    value = "true"
  }

  set {
    name  = "autoscaling.minReplicas"
    value = "3"
  }

  set {
    name  = "autoscaling.maxReplicas"
    value = "10"
  }
}
