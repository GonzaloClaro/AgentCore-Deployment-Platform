# Runtime sin memory (memory_id = null) y en modo zip (no container).

module "runtime" {
  source = "../../modules/runtime"

  name     = local.runtime_name
  role_arn = local.effective_runtime_role_arn

  # Modo zip: el zip vino de package_artifact y vive en S3.
  code_s3_bucket       = var.code_s3_bucket
  code_s3_prefix       = var.code_s3_prefix
  code_entry_point     = [var.runtime.entrypoint]
  code_runtime_version = var.runtime.runtime_version

  env_vars    = var.runtime.env
  memory_id   = null
  pipeline_id = var.pipeline_id
  tags        = local.base_tags
  models      = var.models
}
