output "agent_runtime_arn" { value = module.runtime.agent_runtime_arn }
output "agent_runtime_alias_arn" { value = module.runtime.agent_runtime_alias_arn }
output "agent_runtime_version" { value = module.runtime.agent_runtime_version }
output "log_group_name" { value = try(module.observability[0].log_group_name, null) }
