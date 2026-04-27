module "runtime" {
  source = "../../modules/runtime"

  name      = local.runtime_name
  role_arn  = local.effective_runtime_role_arn # local viene de runtime_role.tf
  image_uri = var.image_uri
  env_vars = merge(
    var.runtime.env,
    local.has_kb ? { KNOWLEDGE_BASE_ID = module.knowledge_base[0].knowledge_base_id } : {}
  )
  memory_id   = module.memory.memory_id
  pipeline_id = var.pipeline_id
  tags        = local.base_tags
  models      = var.models
}
