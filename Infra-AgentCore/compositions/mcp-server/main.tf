# compositions/mcp-server
# MCP server detrás de un default gateway con autorización.
#
# Estructura:
#   main.tf            — terraform/provider/locals
#   runtime.tf         — runtime que sirve el MCP
#   oauth_provider.tf  — OAuth2 credential provider (opcional, var.oauth_provider != null)
#   gateway_targets.tf — targets en gateway por defecto
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
      Kind        = "mcp"
    }
  )
  gateways_by_name = {
    "oauth-3lo" = var.default_gateway_ids.oauth_3lo
    "oauth-2lo" = var.default_gateway_ids.oauth_2lo
    "sigv4-m2m" = var.default_gateway_ids.sigv4_m2m
  }
}
