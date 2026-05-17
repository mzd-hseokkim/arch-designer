# ADR-0003: One SQS queue per channel + shared DLQ.
locals {
  channels = ["naver", "coupang", "ownsite"]
}

resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name}-dlq"
  message_retention_seconds = 1209600 # 14 days
  kms_master_key_id         = "alias/aws/sqs"
}

resource "aws_sqs_queue" "channel" {
  for_each = toset(local.channels)

  name                       = "${local.name}-${each.key}"
  visibility_timeout_seconds = 60
  message_retention_seconds  = 1209600
  kms_master_key_id          = "alias/aws/sqs"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 5
  })
}

# SNS Mobile Push (FCM bridge) — push platform application is provisioned via FCM creds
# (Secrets Manager); SNS-side resource here is the topic that notification-worker publishes to.
resource "aws_sns_topic" "mobile_push" {
  name              = "${local.name}-mobile-push"
  kms_master_key_id = "alias/aws/sns"
}
