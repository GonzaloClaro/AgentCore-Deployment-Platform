# compositions/gateway-deploy
# Despliega un gateway custom (no uno de los 3 default), con targets pointing a recursos
# pre-existentes (Lambdas, OpenAPI schemas) y opcionalmente un policy engine Cedar.
#
# Para qué sirve: capabilities que necesitan un gateway aislado (policy engine separado,
# autenticación dedicada, blast radius reducido).
#
# Estructura:
#   main.tf            — terraform/provider/locals
#   gateway.tf         — el gateway nuevo
#   gateway_targets.tf — targets opcionales (referencian ARNs externos)
#   gateway_policy.tf  — policy engine Cedar opcional

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
  gateway_name = "${var.name}-${var.environment}"
  base_tags = merge(
    { for t in var.tags : t => "true" },
    {
      Capability  = var.capability
      Owner       = var.owner
      Environment = var.environment
      Domain      = "agentcore"
      Kind        = "gateway"
    }
  )
}
