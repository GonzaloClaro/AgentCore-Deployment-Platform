# Cedar policies opcionales sobre los gateways usados por este agente.
# Activable con features.enable_policies = true + spec.gateway_policies[].
# El componente CI apply_policy lee los .cedar files del workload y los pasa via tfvars.

module "gateway_policies" {
  for_each = lookup(var.features, "enable_policies", false) ? {
    for idx, p in var.gateway_policies : "${p.gateway}-${idx}" => p
  } : {}

  source = "../../modules/gateway-policy"

  name           = replace("${local.runtime_name}-${each.value.gateway}-policies", "-", "_")
  description    = "Cedar policies de ${local.runtime_name} en gateway ${each.value.gateway}"
  gateway_name   = each.value.gateway
  attach_mode    = lookup(each.value, "attach_mode", "LOGONLY")
  cedar_policies = each.value.cedar_policies
}
