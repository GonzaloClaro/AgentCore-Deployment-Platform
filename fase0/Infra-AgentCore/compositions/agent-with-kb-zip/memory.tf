module "memory" {
  source = "../../modules/memory"

  name        = "${local.runtime_name}-memory"
  description = "Memory para ${local.runtime_name}"
  strategies = var.memory.strategy == "none" ? [] : [{
    name          = var.memory.strategy
    type          = upper(replace(var.memory.strategy, "-", "_"))
    namespaces    = ["/"]
    configuration = null
  }]
  tags = local.base_tags
}
