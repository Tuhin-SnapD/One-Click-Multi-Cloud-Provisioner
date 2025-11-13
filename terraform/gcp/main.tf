# GCP Infrastructure Configuration
# This file defines the main infrastructure components for GCP

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Uncomment and configure for remote state management
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "gcp/${var.environment}/terraform.tfstate"
  # }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${var.environment}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.compute]
}

# Public Subnet
resource "google_compute_subnetwork" "public" {
  count         = length(var.public_subnet_cidrs)
  name          = "${var.environment}-public-subnet-${count.index + 1}"
  ip_cidr_range = var.public_subnet_cidrs[count.index]
  region        = var.gcp_region
  network       = google_compute_network.main.id

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
  }
}

# Private Subnet
resource "google_compute_subnetwork" "private" {
  count         = length(var.private_subnet_cidrs)
  name          = "${var.environment}-private-subnet-${count.index + 1}"
  ip_cidr_range = var.private_subnet_cidrs[count.index]
  region        = var.gcp_region
  network       = google_compute_network.main.id

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
  }
}

# Cloud Router for NAT
resource "google_compute_router" "main" {
  count   = var.enable_nat ? 1 : 0
  name    = "${var.environment}-router"
  region  = var.gcp_region
  network = google_compute_network.main.id
}

# Cloud NAT
resource "google_compute_router_nat" "main" {
  count                              = var.enable_nat ? 1 : 0
  name                               = "${var.environment}-nat"
  router                             = google_compute_router.main[0].name
  region                             = var.gcp_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall Rule - Allow SSH
resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.environment}-allow-ssh"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]  # Restrict in production
  target_tags   = ["ssh"]
}

# Firewall Rule - Allow HTTP
resource "google_compute_firewall" "allow_http" {
  name    = "${var.environment}-allow-http"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http"]
}

# Firewall Rule - Allow HTTPS
resource "google_compute_firewall" "allow_https" {
  name    = "${var.environment}-allow-https"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https"]
}

# Firewall Rule - Allow Prometheus
resource "google_compute_firewall" "allow_prometheus" {
  name    = "${var.environment}-allow-prometheus"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["9090", "9100"]
  }

  source_ranges = [var.vpc_cidr]
  target_tags   = ["prometheus"]
}

# Firewall Rule - Allow Internal
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.environment}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  source_ranges = [var.vpc_cidr]
}

# Compute Instances
resource "google_compute_instance" "app" {
  count        = var.instance_count
  name         = "${var.environment}-app-instance-${count.index + 1}"
  machine_type = var.instance_type
  zone         = var.gcp_zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30
      type  = "pd-ssd"
    }
  }

  network_interface {
    network    = google_compute_network.main.name
    subnetwork = google_compute_subnetwork.public[count.index % length(google_compute_subnetwork.public)].name

    access_config {
      # Ephemeral public IP
    }
  }

  metadata = {
    ssh-keys = var.ssh_public_key != "" ? "${var.ssh_user}:${var.ssh_public_key}" : null
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y python3 python3-pip
  EOF

  tags = ["ssh", "http", "https"]

  service_account {
    email  = google_service_account.instance.email
    scopes = ["cloud-platform"]
  }
}

# Service Account for Instances
resource "google_service_account" "instance" {
  account_id   = "${var.environment}-instance-sa"
  display_name = "Service Account for Compute Instances"
}

# IAM Role for Service Account
resource "google_project_iam_member" "instance" {
  project = var.gcp_project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.instance.email}"
}

# Cloud SQL Instance (MySQL)
resource "google_sql_database_instance" "main" {
  count            = var.enable_db ? 1 : 0
  name             = "${var.environment}-db-instance"
  database_version = "MYSQL_8_0"
  region           = var.gcp_region

  settings {
    tier              = var.db_instance_tier
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 20
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "prod"
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.main.id
      enable_private_path_for_google_cloud_services = true
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = var.environment == "prod"

  depends_on = [
    google_service_networking_connection.private_vpc_connection,
    google_project_service.sqladmin
  ]
}

# Cloud SQL Database
resource "google_sql_database" "main" {
  count    = var.enable_db ? 1 : 0
  name     = var.db_name
  instance = google_sql_database_instance.main[0].name
}

# Cloud SQL User
resource "google_sql_user" "main" {
  count    = var.enable_db ? 1 : 0
  name     = var.db_username
  instance = google_sql_database_instance.main[0].name
  password = var.db_password
}

# Private Service Connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  count         = var.enable_db ? 1 : 0
  name          = "${var.environment}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_db ? 1 : 0
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]
}

# Enable required APIs
resource "google_project_service" "compute" {
  project = var.gcp_project_id
  service = "compute.googleapis.com"

  disable_dependent_services = false
}

resource "google_project_service" "sqladmin" {
  count   = var.enable_db ? 1 : 0
  project = var.gcp_project_id
  service = "sqladmin.googleapis.com"

  disable_dependent_services = false
}

resource "google_project_service" "servicenetworking" {
  count   = var.enable_db ? 1 : 0
  project = var.gcp_project_id
  service = "servicenetworking.googleapis.com"

  disable_dependent_services = false
}

