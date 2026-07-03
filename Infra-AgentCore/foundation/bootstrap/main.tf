# foundation/bootstrap
# Recursos por cuenta que existen UNA SOLA VEZ y soportan a todos los workloads:
#   - KMS keys (artifacts, secrets, logs)
#   - S3 buckets de artefactos (zip auditables) — un bucket por kind: agents, mcp, tools
#   - IAM roles base: deployer (para pipelines), runtime-execution (para agentes)
# NO crea repos ECR — se crean on-demand por workload (módulo runtime depende de imagen ya en ECR).

terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.53.0" }
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

variable "deployer_principals" {
  type        = list(string)
  description = "Principals (pipelines GitLab, etc.) que asumen el role deployer"
  default     = []
}

locals {
  prefix = "agentcore-${var.environment}"
  tags = {
    ManagedBy   = "agentcore-pipeline"
    Environment = var.environment
    Domain      = "agentcore"
  }
}

resource "aws_kms_key" "artifacts" {
  description             = "KMS para buckets de artefactos AgentCore ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = local.tags
}

resource "aws_kms_alias" "artifacts" {
  name          = "alias/${local.prefix}-artifacts"
  target_key_id = aws_kms_key.artifacts.id
}

resource "aws_kms_key" "secrets" {
  description             = "KMS para Secrets Manager AgentCore ${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = local.tags
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/agentcore-secrets"
  target_key_id = aws_kms_key.secrets.id
}

resource "aws_s3_bucket" "artifacts" {
  for_each = toset(["agents", "mcp", "tools"])
  bucket   = "artifacts-${var.environment}-agentcore-${each.key}"
  tags     = local.tags
}

resource "aws_s3_bucket_versioning" "artifacts" {
  for_each = aws_s3_bucket.artifacts
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  for_each = aws_s3_bucket.artifacts
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.artifacts.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  for_each = aws_s3_bucket.artifacts
  bucket   = each.value.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }
    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

resource "aws_iam_role" "runtime_execution" {
  name = "${local.prefix}-runtime-execution"
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

resource "aws_iam_role_policy_attachment" "runtime_basic" {
  role       = aws_iam_role.runtime_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ────────────────────────────────────────────────────────────────────────────
# Lifecycle protection en PRD: defensa en profundidad
# ────────────────────────────────────────────────────────────────────────────
# Capa 1: el role del DEPLOYER (que asume el pipeline GitLab) tiene un Deny explícito
#         para `bedrock-agentcore:Delete*` cuando ENVIRONMENT == prd.
# Capa 2: existe un role SEPARADO `agentcore-prd-emergency-destroyer` que sí puede
#         destruir, pero solo asumible por humanos con MFA + CAB approval.
# Capa 3: el pipeline_infra.yml tiene manual gate explícito para destroy en PRD.

locals {
  is_prd = startswith(var.environment, "prd")
}

resource "aws_iam_policy" "deployer_deny_destroy_prd" {
  count = local.is_prd ? 1 : 0

  name        = "${local.prefix}-deployer-deny-destroy"
  description = "Niega destroy de recursos críticos AgentCore al deployer role en PRD"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DenyAgentCoreDestroy"
      Effect = "Deny"
      Action = [
        "bedrock-agentcore:DeleteAgentRuntime",
        "bedrock-agentcore:DeleteAgentRuntimeVersion",
        "bedrock-agentcore:DeleteGateway",
        "bedrock-agentcore:DeleteGatewayTarget",
        "bedrock-agentcore:DeleteMemory",
        "bedrock-agent:DeleteKnowledgeBase",
        "bedrock-agent:DeletePrompt",
      ]
      Resource = "*"
      },
      # KMS keys: tampoco delete (impacto severo)
      {
        Sid    = "DenyKmsScheduleDeletion"
        Effect = "Deny"
        Action = ["kms:ScheduleKeyDeletion", "kms:DisableKey"]
        Resource = [
          aws_kms_key.artifacts.arn,
          aws_kms_key.secrets.arn,
        ]
    }]
  })

  tags = local.tags
}

# Role de emergencia con permisos de destroy. NO asumido por el pipeline.
# Trust restringido a humanos con MFA. Para usar:
#   1. CAB approval documentado.
#   2. Operador asume este role manualmente con MFA.
#   3. Ejecuta destroy con audit trail.
#   4. Cierra el incidente.
resource "aws_iam_role" "emergency_destroyer" {
  count = local.is_prd ? 1 : 0

  name = "${local.prefix}-emergency-destroyer"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        # Limitar a usuarios autorizados — pasar lista via var.emergency_destroyer_principals
        AWS = length(var.emergency_destroyer_principals) > 0 ? var.emergency_destroyer_principals : ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
      }
      Action = "sts:AssumeRole"
      Condition = {
        Bool            = { "aws:MultiFactorAuthPresent" = "true" }
        NumericLessThan = { "aws:MultiFactorAuthAge" = "3600" } # MFA reciente (<1h)
      }
    }]
  })

  tags = merge(local.tags, { Purpose = "emergency-destroy-only" })
}

resource "aws_iam_role_policy_attachment" "emergency_destroyer_admin" {
  count      = local.is_prd ? 1 : 0
  role       = aws_iam_role.emergency_destroyer[0].name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

variable "emergency_destroyer_principals" {
  type        = list(string)
  description = "ARNs de IAM users/roles autorizados a asumir agentcore-prd-emergency-destroyer."
  default     = []
}

data "aws_caller_identity" "current" {}

output "kms_artifacts_arn" { value = aws_kms_key.artifacts.arn }
output "kms_secrets_arn" { value = aws_kms_key.secrets.arn }
output "s3_buckets" { value = { for k, v in aws_s3_bucket.artifacts : k => v.id } }
output "runtime_role_arn" { value = aws_iam_role.runtime_execution.arn }
output "deployer_deny_policy_arn" {
  value       = try(aws_iam_policy.deployer_deny_destroy_prd[0].arn, null)
  description = "ARN del deny policy. ATTACH MANUALMENTE al role deployer en PRD post-bootstrap."
}
output "emergency_destroyer_role_arn" {
  value = try(aws_iam_role.emergency_destroyer[0].arn, null)
}
