# ─── ElastiCache Redis Module ───

variable "cluster_id" { type = string }
variable "node_type" { type = string }
variable "num_cache_nodes" { type = number }
variable "engine_version" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "allowed_cidr_blocks" { type = list(string) }

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.cluster_id}-subnet-group"
  subnet_ids = var.subnet_ids
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.cluster_id}-sg"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
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

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = var.cluster_id
  description          = "COS-AA Redis cluster"

  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_nodes
  engine_version       = var.engine_version
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  automatic_failover_enabled = var.num_cache_nodes > 1

  snapshot_retention_limit = 3
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"
}

output "endpoint" {
  value = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  value = aws_elasticache_replication_group.this.port
}
