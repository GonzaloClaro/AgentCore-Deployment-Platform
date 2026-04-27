resource "aws_iam_role" "gateway" {
  name = "${local.gateway_name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.base_tags
}

module "gateway" {
  source = "../../modules/gateway"

  name                     = local.gateway_name
  description              = var.description
  authorizer_type          = var.authorizer_type
  authorizer_configuration = var.authorizer_configuration
  role_arn                 = aws_iam_role.gateway.arn
  tags                     = local.base_tags
}
