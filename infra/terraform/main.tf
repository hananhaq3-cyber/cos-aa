# ─── COS-AA Cloud Infrastructure ───
# Provisions EKS cluster, RDS PostgreSQL, ElastiCache Redis, and supporting resources.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "cos-aa-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "cos-aa-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "COS-AA"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ─── VPC ───
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

# ─── EKS Cluster ───
module "eks" {
  source = "./modules/eks"

  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = "1.29"
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnets

  node_groups = {
    general = {
      instance_types = ["m6i.large"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3
    }
    agents = {
      instance_types = ["c6i.large"]
      min_size       = 1
      max_size       = 8
      desired_size   = 2
      labels = {
        workload = "agent"
      }
    }
  }
}

# ─── RDS PostgreSQL ───
module "rds" {
  source = "./modules/rds"

  identifier     = "${var.project_name}-${var.environment}-db"
  engine_version = "16.1"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.medium"

  allocated_storage     = 50
  max_allocated_storage = 200

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  allowed_cidr_blocks = module.vpc.private_subnets_cidr_blocks

  database_name = "cos_aa"
  username      = "cos_admin"

  multi_az               = var.environment == "production"
  backup_retention_period = var.environment == "production" ? 14 : 3
  deletion_protection     = var.environment == "production"

  extensions = ["pgvector", "uuid-ossp"]
}

# ─── ElastiCache Redis ───
module "elasticache" {
  source = "./modules/elasticache"

  cluster_id     = "${var.project_name}-${var.environment}-redis"
  node_type      = var.environment == "production" ? "cache.r6g.large" : "cache.t3.medium"
  num_cache_nodes = var.environment == "production" ? 3 : 1
  engine_version  = "7.0"

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnets
  allowed_cidr_blocks = module.vpc.private_subnets_cidr_blocks
}

# ─── Outputs ───
output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  value     = module.rds.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value     = module.elasticache.endpoint
  sensitive = true
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
