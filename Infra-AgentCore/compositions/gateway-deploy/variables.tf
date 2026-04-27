variable "name" { type = string }
variable "capability" { type = string }
variable "environment" { type = string }

variable "owner" {
  type    = string
  default = ""
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "description" {
  type    = string
  default = ""
}

variable "authorizer_type" {
  type        = string
  description = "CUSTOM_JWT (3LO/2LO via JWT) | AWS_IAM (SigV4)"
  default     = "CUSTOM_JWT"
}

variable "authorizer_configuration" {
  type        = any
  description = "Configuración del authorizer (depende del tipo)"
  default     = null
}

variable "tags" {
  type    = list(string)
  default = []
}

variable "gateway_targets" {
  type = list(object({
    name                               = string
    description                        = optional(string, "")
    target_kind                        = string               # lambda | open_api | smithy
    target_arn                         = optional(string, "") # para lambda
    target_s3_uri                      = optional(string, "") # para open_api / smithy
    credential_provider_configurations = optional(any, [])
  }))
  default = []
}

variable "cedar_policies" {
  type        = list(string)
  description = "Lista de policies Cedar (contenido completo del archivo .cedar). Vacío = sin policy engine."
  default     = []
}

variable "policy_attach_mode" {
  type        = string
  description = "ENFORCE = bloquea según policies. LOGONLY = solo loggea (recomendado al inicio)."
  default     = "LOGONLY"
}

variable "features" {
  type    = map(bool)
  default = {}
}

variable "pipeline_id" {
  type    = string
  default = "manual"
}
