# Registra la Lambda como target en uno o más gateways por defecto.
# var.gateway_targets[].gateway selecciona oauth-3lo | oauth-2lo | sigv4-m2m.

module "gateway_targets" {
  for_each = { for idx, t in var.gateway_targets : "${t.gateway}-${idx}" => t }
  source   = "../../modules/gateway-target"

  gateway_identifier = local.gateways_by_name[each.value.gateway]
  name               = "${local.tool_name}-${each.value.gateway}"
  description        = "Tool Lambda ${local.tool_name} expuesta via gateway ${each.value.gateway}"
  target_configuration = {
    mcp = {
      lambda = {
        lambda_arn = module.lambda.function_arn
      }
    }
  }
  credential_provider_configurations = []
}
