# compositions/agent-base
# Composición mínima absoluta: runtime + observability. SIN memory.
# Para agentes stateless: clasificadores, traductores, validadores, agentes determinísticos.
#
# Estructura:
#   main.tf            — terraform/provider/locals
#   runtime.tf         — el agent runtime (memory_id = null)
#   observability.tf   — log group, X-Ray, dashboard (con flag)

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.42.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  runtime_name = "${var.name}-${var.environment}"
  base_tags = merge(
    { for t in var.tags : t => "true" },
    {
      Capability  = var.capability
      Owner       = var.owner
      Environment = var.environment
      Domain      = "agentcore"
      Stateless   = "true"
    }
  )
}
