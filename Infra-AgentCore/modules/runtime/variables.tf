variable "name" {
  type        = string
  description = "Nombre del runtime (kebab-case)"
}

variable "role_arn" {
  type        = string
  description = "IAM role para ejecución del runtime"
}

variable "image_uri" {
  type        = string
  description = "ECR URI ARM64 de la imagen del agente"
}

variable "server_protocol" {
  type        = string
  description = "Protocolo HTTP/HTTPS"
  default     = "HTTP"
}

variable "network_mode" {
  type        = string
  description = "PUBLIC | VPC"
  default     = "PUBLIC"
}

variable "env_vars" {
  type        = map(string)
  description = "Variables de entorno del contenedor"
  default     = {}
}

variable "memory_id" {
  type        = string
  description = "ID de Memory asociado (opcional)"
  default     = null
}

variable "pipeline_id" {
  type        = string
  description = "ID del pipeline que originó la versión (para descripción de la version)"
  default     = "manual"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "models" {
  type = list(object({
    alias                 = string
    provider              = string # bedrock | azure
    model_id              = string
    region                = string
    inference_profile_arn = string
    endpoint              = string # azure
    deployment            = string # azure
    api_version           = string # azure
    api_key_secret_arn    = string # azure (ARN de Secrets Manager)
  }))
  description = "Modelos LLM declarados en spec.models[]. Se proyectan como env vars con prefijo del alias."
  default     = []
}
