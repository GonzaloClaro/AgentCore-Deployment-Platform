output "agent_runtime_id" {
  value = aws_bedrockagentcore_agent_runtime.this.agent_runtime_id
}

output "agent_runtime_arn" {
  value = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "agent_runtime_version" {
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_version
  description = "Versión actual del runtime; computed, auto-incrementa con cada update."
}

# Provider 6.x eliminó el recurso aws_bedrockagentcore_agent_runtime_alias. Mantenemos este output
# por compat con downstream (compositions/*/outputs.tf, mcp-server/gateway_targets.tf) apuntando al
# arn del runtime. Para rollback inmutable, usar la API directa de AgentCore (UpdateAgentRuntime con
# version anterior) hasta que el provider vuelva a soportar alias.
output "agent_runtime_alias_arn" {
  value       = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
  description = "Alias ARN — actualmente igual al runtime ARN (alias no soportado en provider 6.x)."
}

output "workload_identity_arn" {
  value       = try(aws_bedrockagentcore_agent_runtime.this.workload_identity_details[0].workload_identity_arn, null)
  description = "Workload Identity creado automáticamente con el runtime"
}

output "models_summary" {
  value = [
    for m in var.models : {
      alias    = m.alias
      provider = m.provider
      model_id = m.model_id
    }
  ]
  description = "Resumen de modelos inyectados al runtime (audit trail)."
}
