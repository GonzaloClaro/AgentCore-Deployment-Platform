# foundation/default-gateways
# 3 gateways AgentCore por defecto del ambiente:
#   1. oauth-3lo  — human-machine OAuth 3LO (JWT authorizer, scopes openid/profile)
#   2. oauth-2lo  — machine-to-machine OAuth 2LO (JWT con client_credentials)
#   3. sigv4-m2m  — machine-to-machine con SigV4 (AWS_IAM authorizer)
# Workloads (agentes/MCP) NO crean gateways; solo agregan TARGETS via módulo gateway-target.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.42.0" }
  }
}

provider "aws" {
  region = var.region
}

variable "environment" { type = string }

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "oauth_3lo_discovery_url" {
  type        = string
  description = "URL OIDC discovery del IdP corporativo para 3LO"
}
variable "oauth_2lo_discovery_url" {
  type        = string
  description = "URL OIDC discovery del IdP para 2LO (típicamente mismo IdP, diferente client)"
}
variable "allowed_audience_3lo" {
  type    = list(string)
  default = []
}
variable "allowed_audience_2lo" {
  type    = list(string)
  default = []
}

locals {
  tags = {
    ManagedBy   = "agentcore-pipeline"
    Environment = var.environment
    Domain      = "agentcore"
    Type        = "default-gateway"
  }
}

resource "aws_iam_role" "gateway" {
  name = "agentcore-${var.environment}-default-gateway"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

module "gw_oauth_3lo" {
  source          = "../../modules/gateway"
  name            = "oauth-3lo"
  description     = "Default gateway: human-machine OAuth 3LO (${var.environment})"
  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration = {
    custom_jwt_authorizer = {
      discovery_url    = var.oauth_3lo_discovery_url
      allowed_audience = var.allowed_audience_3lo
    }
  }
  role_arn = aws_iam_role.gateway.arn
  tags     = local.tags
}

module "gw_oauth_2lo" {
  source          = "../../modules/gateway"
  name            = "oauth-2lo"
  description     = "Default gateway: machine-machine OAuth 2LO (${var.environment})"
  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration = {
    custom_jwt_authorizer = {
      discovery_url    = var.oauth_2lo_discovery_url
      allowed_audience = var.allowed_audience_2lo
    }
  }
  role_arn = aws_iam_role.gateway.arn
  tags     = local.tags
}

module "gw_sigv4" {
  source          = "../../modules/gateway"
  name            = "sigv4-m2m"
  description     = "Default gateway: machine-machine SigV4 (${var.environment})"
  authorizer_type = "AWS_IAM"
  role_arn        = aws_iam_role.gateway.arn
  tags            = local.tags
}

output "gateway_oauth_3lo_id" { value = module.gw_oauth_3lo.gateway_id }
output "gateway_oauth_2lo_id" { value = module.gw_oauth_2lo.gateway_id }
output "gateway_sigv4_id" { value = module.gw_sigv4.gateway_id }
