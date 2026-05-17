variable "region" {
  description = "AWS region. ap-northeast-2 enforced by data residency NFR (§3.6)."
  type        = string
  default     = "ap-northeast-2"
}

variable "environment" {
  description = "Environment name (dev/stg/prd)."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "azs" {
  description = "Availability Zones. ADR-0005 requires 3 AZ."
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"]
}

variable "api_image" {
  description = "Container image for api-gateway-svc. Pinned tag; never 'latest'."
  type        = string
  default     = "EXAMPLE_account.dkr.ecr.ap-northeast-2.amazonaws.com/order-service/api:0.1.0"
}

variable "api_desired_count" {
  description = "Min replicas. ADR-0005: spread across AZs ⇒ ≥2."
  type        = number
  default     = 2
}

variable "aurora_min_acu" {
  description = "Aurora Serverless v2 min ACU."
  type        = number
  default     = 0.5
}

variable "aurora_max_acu" {
  description = "Aurora Serverless v2 max ACU."
  type        = number
  default     = 4
}

variable "db_master_username" {
  description = "Aurora master username. Password is generated and stored in Secrets Manager."
  type        = string
  default     = "orders_admin"
}
