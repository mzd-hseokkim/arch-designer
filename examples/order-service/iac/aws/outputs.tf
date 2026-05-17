output "vpc_id" {
  value = module.vpc.vpc_id
}

output "ecs_cluster_arn" {
  value = module.ecs_cluster.arn
}

output "alb_dns_name" {
  value = module.alb.dns_name
}

output "aurora_endpoint" {
  value     = module.aurora.cluster_endpoint
  sensitive = true
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.sellers.id
}

output "channel_queue_arns" {
  value = { for c, q in aws_sqs_queue.channel : c => q.arn }
}
