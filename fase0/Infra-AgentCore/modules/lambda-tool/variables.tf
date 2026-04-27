variable "name" { type = string }

variable "s3_bucket" {
  type        = string
  description = "Bucket donde está el zip empaquetado por package_artifact"
}

variable "s3_key" {
  type        = string
  description = "Key del zip"
}

variable "handler" {
  type    = string
  default = "tool.handler"
}

variable "runtime_version" {
  type    = string
  default = "python3.12"
}

variable "timeout_seconds" {
  type    = number
  default = 30
}

variable "memory_mb" {
  type    = number
  default = 512
}

variable "env_vars" {
  type    = map(string)
  default = {}
}

variable "inline_policies" {
  type = list(object({
    name            = string
    policy_document = string
  }))
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
