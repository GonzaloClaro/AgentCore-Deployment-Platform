# modules/runtime (fase 0 — solo zip mode)
# Crea AgentCore Runtime usando code_configuration con zip en S3.
# Diferencia con la versión global: NO usa container_configuration ni ECR.
# La versión es atributo computed que el provider auto-incrementa con cada update.
# Issue conocido #45099: ENIs pueden quedar huérfanas en destroy.

locals {
  # Proyectar var.models[] → map de env vars con prefijo del alias.
  model_env_vars = merge([
    for m in var.models : merge(
      {
        "${m.alias}_MODEL_ID"       = m.model_id
        "${m.alias}_MODEL_PROVIDER" = m.provider
        "${m.alias}_MODEL_REGION"   = m.region
      },
      m.inference_profile_arn != "" ? {
        "${m.alias}_MODEL_INFERENCE_PROFILE_ARN" = m.inference_profile_arn
      } : {},
      m.provider == "azure" ? {
        "${m.alias}_MODEL_ENDPOINT"           = m.endpoint
        "${m.alias}_MODEL_DEPLOYMENT"         = m.deployment
        "${m.alias}_MODEL_API_VERSION"        = m.api_version
        "${m.alias}_MODEL_API_KEY_SECRET_ARN" = m.api_key_secret_arn
      } : {}
    )
  ]...)

  memory_env_var = var.memory_id != null ? { AGENTCORE_MEMORY_ID = var.memory_id } : {}

  # AgentCore exige snake_case en agent_runtime_name
  runtime_name_normalized = replace(var.name, "-", "_")
}

resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = local.runtime_name_normalized
  role_arn           = var.role_arn
  description        = "Pipeline ${var.pipeline_id} (zip mode)"

  agent_runtime_artifact {
    code_configuration {
      entry_point = var.code_entry_point
      runtime     = var.code_runtime_version
      code {
        s3 {
          bucket = var.code_s3_bucket
          prefix = var.code_s3_prefix
        }
      }
    }
  }

  network_configuration {
    network_mode = var.network_mode
  }

  environment_variables = merge(var.env_vars, local.model_env_vars, local.memory_env_var)

  tags = merge(var.tags, {
    Name      = var.name
    ManagedBy = "agentcore-pipeline-fase0"
  })

  lifecycle {
    create_before_destroy = true
  }
}
