output "log_group_name" {
  value = aws_cloudwatch_log_group.agent.name
}

output "dashboard_name" {
  value = try(aws_cloudwatch_dashboard.agent[0].dashboard_name, null)
}
