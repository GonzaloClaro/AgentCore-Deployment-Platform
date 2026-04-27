output "lambda_arn" { value = module.lambda.function_arn }
output "lambda_name" { value = module.lambda.function_name }
output "gateway_target_ids" { value = { for k, m in module.gateway_targets : k => m.target_id } }
