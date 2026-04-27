# Runtime sin memory (memory_id = null en el módulo runtime).

module "runtime" {
  source = "../../modules/runtime"

  name = local.runtime_name
  # Si runtime_iam declarado → role custom; si no → default compartido. Local viene de runtime_role.tf
  role_arn    = local.effective_runtime_role_arn
  image_uri   = var.image_uri
  env_vars    = var.runtime.env
  memory_id   = null
  pipeline_id = var.pipeline_id
  tags        = local.base_tags
  models      = var.models
}
