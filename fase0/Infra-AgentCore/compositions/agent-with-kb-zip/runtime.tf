# Runtime con memory + KB en modo zip (no container).

module "runtime" {
  source = "../../modules/runtime"

  name     = local.runtime_name
  role_arn = local.effective_runtime_role_arn

  # Modo zip
  code_s3_bucket       = var.code_s3_bucket
  code_s3_prefix       = var.code_s3_prefix
  code_entry_point     = [var.runtime.entrypoint]
  code_runtime_version = var.runtime.runtime_version

  env_vars = merge(
    var.runtime.env,
    local.has_kb ? { KNOWLEDGE_BASE_ID = module.knowledge_base[0].knowledge_base_id } : {}
  )
  memory_id   = module.memory.memory_id
  pipeline_id = var.pipeline_id
  tags        = local.base_tags
  models      = var.models
}
