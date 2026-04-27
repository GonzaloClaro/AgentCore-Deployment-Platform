output "policy_engine_name" {
  value = var.name
}

output "policy_count" {
  value = length(var.cedar_policies)
}

output "trigger_id" {
  value       = null_resource.policy_engine.id
  description = "ID del null_resource (cambia cuando los policies cambian → re-aplica)"
}

output "attach_mode" {
  value = var.attach_mode
}
