# modules/runtime-role
# Crea un IAM role dedicado para el runtime de un workload, con policies opcionales:
#   - managed_policy_arns:  ARNs de managed policies ya creadas (camino recomendado, ownership de accesos)
#   - inline_policies:      JSONs declarados en el manifest (camino self-service, gate de aprobación QA/PRD)
#
# Por qué role per-workload (en lugar de usar el default compartido):
#   - Aislamiento: cambios IAM de un workload no afectan a otros.
#   - Auditoría: el role del runtime tiene blast radius acotado al workload.
#   - Permission boundary: cada role queda bajo un boundary corporativo opcional.
#
# Si el manifest NO declara runtime_iam, las composiciones siguen usando el default_role_arn
# del env-defaults — este módulo NO se invoca en ese caso.

resource "aws_iam_role" "runtime" {
  name = "${var.runtime_name}-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock-agentcore.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  permissions_boundary = var.permissions_boundary_arn # null si no aplica
  tags                 = merge(var.tags, { Name = "${var.runtime_name}-execution" })
}

# CloudWatch logs base — siempre se attacha
resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.runtime.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Bedrock model invoke base — el runtime típicamente llama a foundation models
resource "aws_iam_role_policy" "bedrock_invoke" {
  count = var.attach_bedrock_invoke ? 1 : 0
  name  = "bedrock-invoke-models"
  role  = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse",
        "bedrock:ConverseStream",
        "bedrock:GetPrompt",
      ]
      Resource = "*"
    }]
  })
}

# Managed policies — el dev declara ARNs ya creados por accesos, este módulo los ataca
resource "aws_iam_role_policy_attachment" "managed" {
  for_each   = toset(var.managed_policy_arns)
  role       = aws_iam_role.runtime.name
  policy_arn = each.value
}

# Inline policies — JSON statements declarados en el manifest del workload
resource "aws_iam_role_policy" "inline" {
  for_each = { for p in var.inline_policies : p.name => p }
  name     = each.value.name
  role     = aws_iam_role.runtime.id
  policy   = each.value.policy_document # string JSON ya leído por apply_policy / render_tfvars
}

# Si hay modelos Azure declarados, el runtime necesita leer su API key de Secrets Manager.
# Inline policy con permiso limitado SOLO a esos ARNs (least privilege).
resource "aws_iam_role_policy" "azure_secrets_read" {
  count = length(var.azure_secret_arns) > 0 ? 1 : 0
  name  = "azure-api-keys-read"
  role  = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.azure_secret_arns
    }]
  })
}
