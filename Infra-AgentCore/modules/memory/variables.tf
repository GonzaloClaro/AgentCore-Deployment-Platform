variable "name" {
  type = string
}

variable "description" {
  type    = string
  default = ""
}

variable "event_expiry_seconds" {
  type        = number
  description = "Tiempo en segundos antes de que los eventos de memoria expiren"
  default     = 2592000 # 30 días
}

variable "strategies" {
  type = list(object({
    name       = string
    type       = string
    namespaces = list(string)
    configuration = optional(object({
      type = string
    }))
  }))
  description = "Lista de memory strategies a crear"
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
