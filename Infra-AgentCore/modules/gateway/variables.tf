variable "name" {
  type = string
}

variable "description" {
  type    = string
  default = ""
}

variable "authorizer_type" {
  type        = string
  description = "CUSTOM_JWT (3LO/2LO via JWT) | AWS_IAM (SigV4)"
}

variable "authorizer_configuration" {
  type        = any
  description = "Bloque específico al authorizer_type"
  default     = null
}

variable "role_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
