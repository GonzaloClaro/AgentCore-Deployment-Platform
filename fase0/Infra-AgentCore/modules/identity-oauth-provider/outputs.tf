output "credential_provider_arn" {
  value = aws_bedrockagentcore_oauth2_credential_provider.this.credential_provider_arn
}

output "credential_provider_name" {
  value = aws_bedrockagentcore_oauth2_credential_provider.this.name
}
