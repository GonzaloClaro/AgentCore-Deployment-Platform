variable "runtime_name" {
  type        = string
  description = "Nombre del runtime (usado para nombrar el role: <runtime_name>-execution)"
}

variable "managed_policy_arns" {
  type        = list(string)
  description = "Lista de ARNs de managed policies ya creadas por el equipo de accesos. Path recomendado."
  default     = []
}

variable "inline_policies" {
  type = list(object({
    name            = string
    policy_document = string # JSON serializado del policy
  }))
  description = "Lista de inline policies declaradas en el manifest del workload (modo self-service, gate QA/PRD)."
  default     = []
}

variable "permissions_boundary_arn" {
  type        = string
  description = "ARN de permission boundary corporativo. null = sin boundary."
  default     = null
}

variable "attach_bedrock_invoke" {
  type        = bool
  description = "Adjunta inline policy con bedrock:InvokeModel/Converse/GetPrompt. true por default — el runtime casi siempre los necesita."
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "azure_secret_arns" {
  type        = list(string)
  description = "ARNs de Secrets Manager con API keys de Azure. Si la lista no está vacía, attacha policy con secretsmanager:GetSecretValue limitado a esos ARNs."
  default     = []
}
