# foundation/vpc-endpoints
# Endpoints VPC para tráfico privado a Bedrock, S3, ECR, Secrets Manager.
# Reduce egreso a internet y mejora seguridad.

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.53.0" }
  }
}

provider "aws" { region = var.region }

variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }

variable "region" {
  type    = string
  default = "us-east-1"
}

locals {
  services = [
    "bedrock-runtime",
    "bedrock-agent-runtime",
    "ecr.api",
    "ecr.dkr",
    "secretsmanager",
    "logs",
    "sts",
  ]
  tags = {
    ManagedBy   = "agentcore-pipeline"
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(local.services)

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.subnet_ids
  security_group_ids  = var.security_group_ids
  private_dns_enabled = true
  tags                = merge(local.tags, { Name = "agentcore-${each.key}" })
}

resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  tags              = merge(local.tags, { Name = "agentcore-s3" })
}
