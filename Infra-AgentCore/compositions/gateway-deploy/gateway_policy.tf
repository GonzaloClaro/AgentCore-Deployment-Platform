# Policy Engine Cedar opcional, attached al gateway custom de esta composition.
# Activable con features.enable_policies = true + lista de policies en var.cedar_policies.

module "policy" {
  count  = lookup(var.features, "enable_policies", false) && length(var.cedar_policies) > 0 ? 1 : 0
  source = "../../modules/gateway-policy"

  name           = replace("${local.gateway_name}_policies", "-", "_")
  description    = "Cedar policy engine para ${local.gateway_name}"
  gateway_name   = local.gateway_name # nombre, no ID (CLI agentcore opera por nombre)
  attach_mode    = var.policy_attach_mode
  cedar_policies = var.cedar_policies
}
