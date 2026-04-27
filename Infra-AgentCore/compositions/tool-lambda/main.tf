# compositions/tool-lambda
# Tool desplegada como Lambda independiente + registrada como target en uno de los 3 default gateways.
# El zip de la lambda lo produce el componente CI package_artifact.
#
# Estructura:
#   main.tf           — terraform/provider/locals
#   lambda.tf         — la función Lambda (módulo lambda-tool)
#   gateway_target.tf — registro del target en gateway por defecto

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws  = { source = "hashicorp/aws", version = "~> 6.42.0" }
    null = { source = "hashicorp/null", version = ">= 3.2" }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  tool_name = "${var.name}-${var.environment}"
  base_tags = merge(
    { for t in var.tags : t => "true" },
    {
      Capability  = var.capability
      Owner       = var.owner
      Environment = var.environment
      Domain      = "agentcore"
      Kind        = "tool"
      ToolMode    = "lambda"
    }
  )
  gateways_by_name = {
    "oauth-3lo" = var.default_gateway_ids.oauth_3lo
    "oauth-2lo" = var.default_gateway_ids.oauth_2lo
    "sigv4-m2m" = var.default_gateway_ids.sigv4_m2m
  }
}
