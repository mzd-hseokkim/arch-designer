# ADR-0002: Aurora PostgreSQL Serverless v2, Multi-AZ.
module "aurora" {
  source  = "terraform-aws-modules/rds-aurora/aws"
  version = "~> 9.10"

  name              = "${local.name}-pg"
  engine            = "aurora-postgresql"
  engine_mode       = "provisioned"
  engine_version    = "15.4"
  storage_encrypted = true

  vpc_id               = module.vpc.vpc_id
  db_subnet_group_name = module.vpc.database_subnet_group_name
  subnets              = module.vpc.intra_subnets # isolated subnets per design §6.1

  master_username             = var.db_master_username
  manage_master_user_password = true

  serverlessv2_scaling_configuration = {
    min_capacity = var.aurora_min_acu
    max_capacity = var.aurora_max_acu
  }

  instance_class = "db.serverless"
  instances = {
    writer = {}
    reader = {} # ADR-0002 multi-AZ; reader in a different AZ
  }

  backup_retention_period      = 14
  preferred_backup_window      = "16:00-17:00" # KST 01:00-02:00
  apply_immediately            = false
  deletion_protection          = true
  performance_insights_enabled = true
  monitoring_interval          = 60

  # ADR-0002 RPO 5 min: continuous backup + PITR enabled by default for Aurora.
}

# ElastiCache Redis (design §6.1) — kept minimal.
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis"
  subnet_ids = module.vpc.intra_subnets
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name}-redis"
  description                = "Sessions, polling cursors, aggregates"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.t4g.small"
  num_cache_clusters         = 2 # writer + replica
  automatic_failover_enabled = true
  multi_az_enabled           = true
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}
