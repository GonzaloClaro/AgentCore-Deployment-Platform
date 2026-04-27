# compositions/agent-with-kb
# Para agentes con RAG: runtime + memory + knowledge-base + observability.
#
# Estructura:
#   main.tf            — terraform/provider/locals
#   runtime.tf         — el agent runtime (con KB ID en env vars)
#   memory.tf          — memory
#   knowledge_base.tf  — Bedrock KB con S3 Vectors
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
    }
  )
  has_kb = length(lookup(var.knowledge_base, "sources", [])) > 0
}
