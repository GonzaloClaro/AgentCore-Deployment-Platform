module "runtime" {
  source = "../../modules/runtime"

  name        = local.runtime_name
  role_arn    = local.effective_runtime_role_arn # local viene de runtime_role.tf
  image_uri   = var.image_uri
  env_vars    = var.runtime.env
  pipeline_id = var.pipeline_id
  tags        = local.base_tags
  models      = var.models
}
