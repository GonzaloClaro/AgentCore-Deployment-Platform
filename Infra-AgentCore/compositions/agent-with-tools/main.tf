# compositions/agent-with-tools
# Agente con tools externas via gateway-target en uno de los 3 default gateways.
#
# Estructura:
#   main.tf            — terraform/provider/locals (incluye lookup de gateway IDs por nombre)
#   runtime.tf
#   memory.tf
#   gateway_targets.tf — uno o más targets, según var.gateway_targets[]
#   observability.tf

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.53.0" }
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
  gateways_by_name = {
    "oauth-3lo" = var.default_gateway_ids.oauth_3lo
    "oauth-2lo" = var.default_gateway_ids.oauth_2lo
    "sigv4-m2m" = var.default_gateway_ids.sigv4_m2m
  }
}
