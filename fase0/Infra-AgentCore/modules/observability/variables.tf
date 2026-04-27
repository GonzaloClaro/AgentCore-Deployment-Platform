variable "runtime_name" { type = string }
variable "runtime_arn" { type = string }
variable "environment" { type = string }

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "enable_xray" {
  type    = bool
  default = true
}

variable "enable_dashboard" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
