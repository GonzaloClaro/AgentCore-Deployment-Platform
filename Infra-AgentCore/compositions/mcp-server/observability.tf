module "observability" {
  count  = lookup(var.features, "enable_observability", true) ? 1 : 0
  source = "../../modules/observability"

  runtime_name     = local.runtime_name
  runtime_arn      = module.runtime.agent_runtime_arn
  environment      = var.environment
  kms_key_arn      = var.kms_key_arn
  enable_dashboard = lookup(var.observability, "dashboard", false)
  tags             = local.base_tags
}
