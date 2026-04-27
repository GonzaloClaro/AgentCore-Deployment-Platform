module "lambda" {
  source = "../../modules/lambda-tool"

  name            = local.tool_name
  s3_bucket       = var.artifact_s3_bucket
  s3_key          = var.artifact_s3_key
  handler         = lookup(var.runtime, "handler", "tool.handler")
  runtime_version = lookup(var.runtime, "runtime_version", "python3.12")
  timeout_seconds = lookup(var.runtime, "timeout_seconds", 30)
  memory_mb       = lookup(var.runtime, "memory_mb", 512)
  env_vars        = lookup(var.runtime, "env", {})
  tags            = local.base_tags
}
