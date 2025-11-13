# Output definitions for AWS infrastructure

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "instance_public_ips" {
  description = "Public IP addresses of EC2 instances"
  value       = aws_instance.app[*].public_ip
}

output "instance_private_ips" {
  description = "Private IP addresses of EC2 instances"
  value       = aws_instance.app[*].private_ip
}

output "instance_ids" {
  description = "IDs of EC2 instances"
  value       = aws_instance.app[*].id
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = var.enable_db ? aws_db_instance.main[0].endpoint : null
}

output "rds_address" {
  description = "RDS instance address"
  value       = var.enable_db ? aws_db_instance.main[0].address : null
}

output "security_group_ids" {
  description = "Security group IDs"
  value = {
    ec2        = aws_security_group.ec2.id
    prometheus = aws_security_group.prometheus.id
    rds        = var.enable_db ? aws_security_group.rds[0].id : null
  }
}

