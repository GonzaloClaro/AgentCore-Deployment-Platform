# modules/lambda-tool
# Lambda ARM64 que sirve como tool exponible via gateway-target.
# El package zip se construye en pipeline (componente package_artifact + build).

resource "aws_iam_role" "lambda" {
  name = "${var.name}-lambda-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "inline" {
  for_each = { for p in var.inline_policies : p.name => p }
  name     = each.value.name
  role     = aws_iam_role.lambda.id
  policy   = each.value.policy_document
}

resource "aws_lambda_function" "this" {
  function_name = var.name
  role          = aws_iam_role.lambda.arn
  architectures = ["arm64"]
  package_type  = "Zip"

  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  handler     = var.handler
  runtime     = var.runtime_version
  timeout     = var.timeout_seconds
  memory_size = var.memory_mb

  environment {
    variables = var.env_vars
  }

  tags = merge(var.tags, { ManagedBy = "agentcore-pipeline" })
}
