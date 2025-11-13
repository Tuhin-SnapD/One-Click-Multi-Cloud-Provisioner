# Variable definitions for GCP infrastructure

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-east1"
}

variable "gcp_zone" {
  description = "GCP zone"
  type        = string
  default     = "us-east1-b"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "enable_nat" {
  description = "Enable Cloud NAT for private subnets"
  type        = bool
  default     = true
}

variable "instance_count" {
  description = "Number of VM instances to create"
  type        = number
  default     = 1
}

variable "instance_type" {
  description = "GCP machine type"
  type        = string
  default     = "n1-standard-1"
}

variable "ssh_user" {
  description = "SSH user for instances"
  type        = string
  default     = "ubuntu"
}

variable "ssh_public_key" {
  description = "SSH public key for instances"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_db" {
  description = "Enable Cloud SQL database"
  type        = bool
  default     = false
}

variable "db_instance_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "appdb"
  sensitive   = true
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  default     = "ChangeMe123!"
  sensitive   = true
}

