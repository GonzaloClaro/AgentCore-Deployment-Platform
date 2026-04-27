variable "name" { type = string }
variable "role_arn" { type = string }
variable "embedding_model_arn" { type = string }

variable "description" {
  type    = string
  default = ""
}

variable "embedding_dimension" {
  type        = number
  description = "Dimensión del embedding (titan-v2 = 1024)"
  default     = 1024
}

variable "sources" {
  type = list(object({
    name               = string
    bucket_arn         = string
    inclusion_prefixes = list(string)
  }))
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
