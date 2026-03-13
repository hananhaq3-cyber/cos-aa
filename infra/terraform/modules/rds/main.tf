# ─── RDS PostgreSQL Module ───

variable "identifier" { type = string }
variable "engine_version" { type = string }
variable "instance_class" { type = string }
variable "allocated_storage" { type = number }
variable "max_allocated_storage" { type = number }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "allowed_cidr_blocks" { type = list(string) }
variable "database_name" { type = string }
variable "username" { type = string }
variable "multi_az" { type = bool }
variable "backup_retention_period" { type = number }
variable "deletion_protection" { type = bool }
variable "extensions" { type = list(string) }

resource "aws_db_subnet_group" "this" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.identifier}-sg"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "this" {
  identifier = var.identifier

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_encrypted     = true

  db_name  = var.database_name
  username = var.username
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az               = var.multi_az
  backup_retention_period = var.backup_retention_period
  deletion_protection     = var.deletion_protection

  performance_insights_enabled = true
  monitoring_interval          = 60

  skip_final_snapshot = true
}

output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "port" {
  value = aws_db_instance.this.port
}
