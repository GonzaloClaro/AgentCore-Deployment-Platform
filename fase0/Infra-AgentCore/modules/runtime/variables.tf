variable "name" {
  type        = string
  description = "Nombre del runtime (kebab-case, se convierte a snake_case internamente)"
}

variable "role_arn" {
  type        = string
  description = "IAM role para ejecución del runtime"
}

# ──────────────────────────────────────────────────────────────────
# Modo de artefacto: SOLO zip en fase 0 (no container)
# ──────────────────────────────────────────────────────────────────
variable "code_s3_bucket" {
  type        = string
  description = "Bucket S3 donde está el zip del agente"
}

variable "code_s3_prefix" {
  type        = string
  description = "Key dentro del bucket donde está el zip (ej: 'agents/myagent.zip')"
}

variable "code_entry_point" {
  type        = list(string)
  description = "Entry point del zip (ej: ['main.py'])"
  default     = ["main.py"]
}

variable "code_runtime_version" {
  type        = string
  description = "Versión de Python soportada por AgentCore"
  default     = "PYTHON_3_13"
}

variable "network_mode" {
  type        = string
  description = "PUBLIC | VPC"
  default     = "PUBLIC"
}

variable "env_vars" {
  type        = map(string)
  description = "Variables de entorno del runtime"
  default     = {}
}

variable "memory_id" {
  type        = string
  description = "ID de Memory asociado (se inyecta como env var AGENTCORE_MEMORY_ID)"
  default     = null
}

variable "pipeline_id" {
  type        = string
  description = "ID del pipeline que originó la versión"
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
    inference_profile_arn = optional(string, "")
    endpoint              = optional(string, "")
    deployment            = optional(string, "")
    api_version           = optional(string, "")
    api_key_secret_arn    = optional(string, "")
  }))
  description = "Modelos LLM declarados en spec.models[]. Se proyectan como env vars con prefijo del alias."
  default     = []
}
