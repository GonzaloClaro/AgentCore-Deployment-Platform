# modules/observability
# CloudWatch log group, X-Ray sampling rule, dashboard de uso para un agent runtime.

resource "aws_cloudwatch_log_group" "agent" {
  name              = "/aws/bedrock-agentcore/${var.runtime_name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_xray_sampling_rule" "agent" {
  count          = var.enable_xray ? 1 : 0
  rule_name      = "${var.runtime_name}-default"
  priority       = 1000
  reservoir_size = 1
  fixed_rate     = 0.1
  host           = "*"
  http_method    = "*"
  service_name   = var.runtime_name
  service_type   = "*"
  url_path       = "*"
  resource_arn   = "*"
  version        = 1
}

resource "aws_cloudwatch_dashboard" "agent" {
  count          = var.enable_dashboard ? 1 : 0
  dashboard_name = "agentcore-${var.environment}-${var.runtime_name}"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/BedrockAgentCore", "Invocations", "AgentRuntimeArn", var.runtime_arn],
            [".", "Errors", ".", "."],
            [".", "Latency", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = data.aws_region.current.name
          title  = "Invocations / Errors / Latency"
        }
      }
    ]
  })
}

data "aws_region" "current" {}
