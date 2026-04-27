# Role IAM custom per-workload, opcional.
# Se activa cuando el manifest declara spec.runtime_iam (managed_policy_arns o inline_policies).
# Si no, el runtime usa var.default_role_arn del env-defaults (compartido).

locals {
  has_azure_models = length([for m in var.models : m if m.provider == "azure" && m.api_key_secret_arn != ""]) > 0
  has_runtime_iam = (
    length(var.runtime_iam.managed_policy_arns) > 0 ||
    length(var.runtime_iam.inline_policies) > 0 ||
    local.has_azure_models
  )
  effective_runtime_role_arn = local.has_runtime_iam ? module.runtime_role[0].role_arn : var.default_role_arn
}

module "runtime_role" {
  count  = local.has_runtime_iam ? 1 : 0
  source = "../../modules/runtime-role"

  runtime_name             = local.runtime_name
  managed_policy_arns      = var.runtime_iam.managed_policy_arns
  inline_policies          = var.runtime_iam.inline_policies
  permissions_boundary_arn = var.permissions_boundary_arn
  attach_bedrock_invoke    = lookup(var.runtime_iam, "attach_bedrock_invoke", true)
  azure_secret_arns        = [for m in var.models : m.api_key_secret_arn if m.provider == "azure" && m.api_key_secret_arn != ""]
  tags                     = local.base_tags
}
