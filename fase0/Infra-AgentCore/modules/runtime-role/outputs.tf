output "role_arn" {
  value = aws_iam_role.runtime.arn
}

output "role_name" {
  value = aws_iam_role.runtime.name
}

output "managed_policy_count" {
  value = length(var.managed_policy_arns)
}

output "inline_policy_count" {
  value = length(var.inline_policies)
}
