# modules/gateway
# Crea un gateway AgentCore. NOTA: en uso productivo, los gateways viven en foundation/default-gateways.
# Este módulo se mantiene como reusable por si una capability necesita un gateway dedicado.

resource "aws_bedrockagentcore_gateway" "this" {
  name          = var.name
  description   = var.description
  protocol_type = "MCP"

  authorizer_type = var.authorizer_type
  role_arn        = var.role_arn

  # authorizer_configuration es bloque opcional. Si var.authorizer_configuration es null
  # (típico para AWS_IAM/SigV4), no se renderiza. Si trae custom_jwt_authorizer, se proyecta.
  dynamic "authorizer_configuration" {
    for_each = var.authorizer_configuration != null ? [var.authorizer_configuration] : []
    content {
      dynamic "custom_jwt_authorizer" {
        for_each = try(authorizer_configuration.value.custom_jwt_authorizer, null) != null ? [authorizer_configuration.value.custom_jwt_authorizer] : []
        content {
          discovery_url    = custom_jwt_authorizer.value.discovery_url
          allowed_audience = try(custom_jwt_authorizer.value.allowed_audience, null)
          allowed_clients  = try(custom_jwt_authorizer.value.allowed_clients, null)
          allowed_scopes   = try(custom_jwt_authorizer.value.allowed_scopes, null)
        }
      }
    }
  }

  tags = merge(var.tags, { ManagedBy = "agentcore-pipeline" })
}
