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

variable "kms_key_arn" {
  type    = string
  default = ""
}

variable "default_role_arn" { type = string }

variable "image_uri" { type = string }

variable "pipeline_id" {
  type    = string
  default = "manual"
}

variable "tags" {
  type    = list(string)
  default = []
}

variable "runtime" {
  type = object({
    entrypoint      = optional(string, "")
    env             = optional(map(string), {})
    memory_strategy = optional(string, "summarization")
  })
  description = "Spec del runtime del manifest: entrypoint (consumido por Dockerfile), env vars, strategy de memory."
}

variable "observability" {
  type    = any
  default = { enabled = true }
}

variable "features" {
  type    = map(bool)
  default = {}
}

variable "runtime_iam" {
  type = object({
    managed_policy_arns = optional(list(string), [])
    inline_policies = optional(list(object({
      name            = string
      policy_document = string
    })), [])
    attach_bedrock_invoke = optional(bool, true)
  })
  description = "IAM policies opcionales sobre el role del runtime. Si vacío → default_role_arn compartido."
  default     = { managed_policy_arns = [], inline_policies = [], attach_bedrock_invoke = true }
}

variable "permissions_boundary_arn" {
  type        = string
  default     = null
  description = "Permission boundary corporativo opcional."
}

variable "models" {
  type = list(object({
    alias                 = string
    provider              = string # bedrock | azure
    model_id              = string
    region                = string
    inference_profile_arn = optional(string, "")
    endpoint              = optional(string, "") # azure
    deployment            = optional(string, "") # azure
    api_version           = optional(string, "") # azure
    api_key_secret_arn    = optional(string, "") # azure (ARN de Secrets Manager)
  }))
  description = "Modelos LLM declarados en spec.models[]. Campos azure son optional para que manifests bedrock no tengan que pasarlos vacíos."
  default     = []
}
