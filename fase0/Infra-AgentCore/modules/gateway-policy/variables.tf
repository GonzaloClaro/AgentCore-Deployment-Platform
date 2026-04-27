variable "name" {
  type        = string
  description = "Nombre del policy engine. Inmutable, único en la cuenta. 1-48 chars, [A-Za-z][A-Za-z0-9_]*."
  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,47}$", var.name))
    error_message = "name debe matchear ^[A-Za-z][A-Za-z0-9_]{0,47}$ (regla AgentCore)."
  }
}

variable "description" {
  type    = string
  default = ""
}

variable "gateway_name" {
  type        = string
  description = "Nombre del gateway al que se asocia (la CLI agentcore opera por nombre, no por ID)."
}

variable "attach_mode" {
  type        = string
  description = "ENFORCE = bloquea según policies. LOGONLY = solo loggea decisiones (shadow mode, recomendado para piloto)."
  default     = "LOGONLY"
  validation {
    condition     = contains(["ENFORCE", "LOGONLY"], var.attach_mode)
    error_message = "attach_mode debe ser ENFORCE o LOGONLY."
  }
}

variable "cedar_policies" {
  type        = list(string)
  description = "Lista de policies Cedar como strings (contenido de los archivos .cedar)."
  default     = []
}

variable "use_native_resource" {
  type        = bool
  description = "Cuando hashicorp/aws agregue aws_bedrockagentcore_policy_engine, switchear a true."
  default     = false
}
