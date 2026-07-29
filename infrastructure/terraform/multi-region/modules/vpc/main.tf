# VPC Network Module for Multi-Region Deployment

resource "google_compute_network" "vpc_network" {
  name                    = "${var.environment}-momento-v5-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "primary_subnet" {
  name          = "${var.environment}-primary-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.primary_region
  network       = google_compute_network.vpc_network.id
  
  private_ip_google_access = true
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.0.2.0/24"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.0.3.0/24"
  }
}

resource "google_compute_subnetwork" "secondary_subnet" {
  name          = "${var.environment}-secondary-subnet"
  ip_cidr_range = "10.1.1.0/24"
  region        = var.secondary_region
  network       = google_compute_network.vpc_network.id
  
  private_ip_google_access = true
  
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.2.0/24"
  }
  
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.1.3.0/24"
  }
}

resource "google_compute_router" "primary_router" {
  name    = "${var.environment}-primary-router"
  region  = var.primary_region
  network = google_compute_network.vpc_network.id
}

resource "google_compute_router_nat" "primary_nat" {
  name                               = "${var.environment}-primary-nat"
  router                             = google_compute_router.primary_router.name
  region                             = var.primary_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = ["${google_compute_subnetwork.primary_subnet.ip_cidr_range}"]
  
  log_config {
    enable = true
    filter = "ALL"
  }
}

resource "google_compute_router" "secondary_router" {
  name    = "${var.environment}-secondary-router"
  region  = var.secondary_region
  network = google_compute_network.vpc_network.id
}

resource "google_compute_router_nat" "secondary_nat" {
  name                               = "${var.environment}-secondary-nat"
  router                             = google_compute_router.secondary_router.name
  region                             = var.secondary_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = ["${google_compute_subnetwork.secondary_subnet.ip_cidr_range}"]
  
  log_config {
    enable = true
    filter = "ALL"
  }
}

resource "google_compute_firewall" "allow_internal" {
  name    = "${var.environment}-allow-internal"
  network = google_compute_network.vpc_network.id
  
  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = [
    google_compute_subnetwork.primary_subnet.ip_cidr_range,
    google_compute_subnetwork.secondary_subnet.ip_cidr_range,
    "10.0.2.0/24", "10.0.3.0/24",
    "10.1.2.0/24", "10.1.3.0/24"
  ]
}

resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.environment}-allow-health-checks"
  network = google_compute_network.vpc_network.id
  
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
  
  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
}

resource "google_compute_firewall" "deny_external" {
  name    = "${var.environment}-deny-external"
  network = google_compute_network.vpc_network.id
  
  deny {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  source_ranges = ["0.0.0.0/0"]
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "primary_region" {
  description = "Primary region"
  type        = string
}

variable "secondary_region" {
  description = "Secondary region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

# Outputs
output "network_name" {
  value = google_compute_network.vpc_network.name
}

output "primary_subnet" {
  value = google_compute_subnetwork.primary_subnet.name
}

output "secondary_subnet" {
  value = google_compute_subnetwork.secondary_subnet.name
}