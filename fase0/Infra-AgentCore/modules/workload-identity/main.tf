# modules/workload-identity
# Workload identity explícito (uso avanzado: cuando se necesita un identity reutilizable
# entre runtimes, no el auto-creado por aws_bedrockagentcore_agent_runtime).

resource "aws_bedrockagentcore_workload_identity" "this" {
  name                                = var.name
  allowed_resource_oauth2_return_urls = var.allowed_oauth_return_urls
}
