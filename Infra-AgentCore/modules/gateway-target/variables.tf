variable "gateway_identifier" {
  type        = string
  description = "ID del gateway al que se agrega el target (uno de los 3 default típicamente). Renombrado desde gateway_id en provider 6.x."
}

variable "name" {
  type = string
}

variable "description" {
  type    = string
  default = ""
}

variable "target_configuration" {
  type        = any
  description = <<-EOT
    Configuración del target. Estructura esperada:
      {
        mcp = {
          lambda          = optional({ lambda_arn = string })
          open_api_schema = optional({ s3 = { uri = string, bucket_owner_account_id = optional(string) } })
          smithy_model    = optional({ s3 = { uri = string, bucket_owner_account_id = optional(string) } })
        }
      }
  EOT
}

variable "credential_provider_configurations" {
  type        = list(any)
  default     = []
  description = <<-EOT
    Lista de credential providers. Cada item es un objeto con UNA de estas keys (provider 6.x schema):
      { oauth = { provider_arn = string, scopes = list(string), grant_type = optional(string) } }
      { gateway_iam_role = {} }
      { api_key = { provider_arn = string, credential_location = optional(string), credential_parameter_name = optional(string), credential_prefix = optional(string) } }
  EOT
}
