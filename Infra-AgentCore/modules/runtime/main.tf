# modules/runtime
# Crea AgentCore Runtime. La versión es un atributo computed (agent_runtime_version) que el
# provider auto-incrementa con cada update. Para rollback ad-hoc se usa la API directa de
# AgentCore — provider 6.x no expone los recursos *_version / *_alias.
# Issue conocido #45099: ENIs pueden quedar huérfanas en destroy.

# Proyectar var.models[] → map de env vars con prefijo del alias.
# Pattern: alias=PRIMARY produce PRIMARY_MODEL_ID, PRIMARY_MODEL_PROVIDER, etc.
# El código del agente lee con os.environ["PRIMARY_MODEL_ID"].
locals {
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

  # memory_id se inyecta como env var — provider 6.x ya no expone "memory" como bloque del
  # agent_runtime; la asociación memory↔runtime queda a cargo del agente, que lee AGENTCORE_MEMORY_ID.
  memory_env_var = var.memory_id != null ? { AGENTCORE_MEMORY_ID = var.memory_id } : {}
}

resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = var.name
  role_arn           = var.role_arn
  description        = "Pipeline ${var.pipeline_id}"

  agent_runtime_artifact {
    container_configuration {
      container_uri = var.image_uri
    }
  }

  network_configuration {
    network_mode = var.network_mode
  }

  protocol_configuration {
    server_protocol = var.server_protocol
  }

  environment_variables = merge(var.env_vars, local.model_env_vars, local.memory_env_var)

  tags = merge(var.tags, {
    Name      = var.name
    ManagedBy = "agentcore-pipeline"
  })

  lifecycle {
    create_before_destroy = true
  }
}
