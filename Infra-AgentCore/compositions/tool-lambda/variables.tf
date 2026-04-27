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

# El zip de la Lambda lo produjo package_artifact y subió a S3
variable "artifact_s3_bucket" { type = string }
variable "artifact_s3_key" { type = string }

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
    handler         = optional(string, "tool.handler")
    runtime_version = optional(string, "python3.12")
    timeout_seconds = optional(number, 30)
    memory_mb       = optional(number, 512)
    env             = optional(map(string), {})
  })
  description = "Spec del runtime de la Lambda: handler, runtime_version, timeout, memory, env. Todos optional con defaults."
}

variable "gateway_targets" {
  type    = list(any)
  default = []
}

variable "default_gateway_ids" {
  type = object({
    oauth_3lo = string
    oauth_2lo = string
    sigv4_m2m = string
  })
  description = "IDs de los 3 gateways por defecto del ambiente; vienen del env-defaults."
}
