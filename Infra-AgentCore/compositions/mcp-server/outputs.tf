output "agent_runtime_arn" { value = module.runtime.agent_runtime_arn }
output "agent_runtime_alias_arn" { value = module.runtime.agent_runtime_alias_arn }
output "oauth_provider_arn" { value = try(module.oauth_provider[0].credential_provider_arn, null) }
output "gateway_target_count" { value = length(module.gateway_targets) }
