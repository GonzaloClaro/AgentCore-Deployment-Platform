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

variable "vpc_id" {
  type    = string
  default = ""
}

variable "subnet_ids" {
  type    = list(string)
  default = []
}

variable "kms_key_arn" {
  type    = string
  default = ""
}

variable "default_role_arn" { type = string }

# ──────────────────────────────────────────────────────────────────
# Modo zip: en fase 0 NO usamos image_uri (ECR/Docker).
# ──────────────────────────────────────────────────────────────────
variable "code_s3_bucket" {
  type        = string
  description = "Bucket S3 con el zip del agente (output de package_artifact)"
}

variable "code_s3_prefix" {
  type        = string
  description = "Key del zip dentro del bucket"
}

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
    entrypoint      = optional(string, "main.py")
    runtime_version = optional(string, "PYTHON_3_13")
    env             = optional(map(string), {})
    memory_strategy = optional(string, "summarization")
  })
  description = "Spec del runtime del manifest: entrypoint del zip, runtime_version, env vars, strategy de memory."
}

variable "memory" {
  type    = object({ strategy = string })
  default = { strategy = "summarization" }
}

variable "knowledge_base" {
  type    = any
  default = {}
}

variable "prompts" {
  type    = list(any)
  default = []
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
  description = "IAM policies opcionales sobre el role del runtime."
  default     = { managed_policy_arns = [], inline_policies = [], attach_bedrock_invoke = true }
}

variable "permissions_boundary_arn" {
  type        = string
  default     = null
  description = "Permission boundary corporativo opcional aplicado al runtime role custom."
}

variable "models" {
  type = list(object({
    alias                 = string
    provider              = string # bedrock | azure
    model_id              = string
    region                = string
    inference_profile_arn = optional(string, "")
    endpoint              = optional(string, "")
    deployment            = optional(string, "")
    api_version           = optional(string, "")
    api_key_secret_arn    = optional(string, "")
  }))
  description = "Modelos LLM declarados en spec.models[]."
  default     = []
}
