output "agent_runtime_arn" { value = module.runtime.agent_runtime_arn }
output "agent_runtime_alias_arn" { value = module.runtime.agent_runtime_alias_arn }
output "memory_id" { value = module.memory.memory_id }
output "knowledge_base_id" { value = try(module.knowledge_base[0].knowledge_base_id, null) }
