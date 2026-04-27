output "gateway_id" { value = module.gateway.gateway_id }
output "gateway_arn" { value = module.gateway.gateway_arn }
output "gateway_url" { value = module.gateway.gateway_url }
output "target_count" { value = length(module.targets) }
output "policy_engine" { value = try(module.policy[0].policy_engine_name, null) }
output "policy_count" { value = try(module.policy[0].policy_count, 0) }
