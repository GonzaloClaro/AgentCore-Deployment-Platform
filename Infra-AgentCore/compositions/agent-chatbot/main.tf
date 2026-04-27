# compositions/agent-chatbot
# Composición mínima: runtime + memory + observability.
# Para chatbots simples sin KB ni tools.
#
# Estructura:
#   main.tf            — terraform/provider/locals (sin recursos)
#   runtime.tf         — el agent runtime
#   memory.tf          — memory + strategy
#   observability.tf   — log group, X-Ray, dashboard (con flag)
#   variables.tf       — inputs tipados
#   outputs.tf         — outputs expuestos al caller

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
    }
  )
}
