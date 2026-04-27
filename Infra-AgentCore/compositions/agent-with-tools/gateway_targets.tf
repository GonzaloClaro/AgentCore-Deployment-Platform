# Gateway targets — uno por cada entry en var.gateway_targets[].
# Cada target referencia uno de los 3 gateways default (oauth-3lo | oauth-2lo | sigv4-m2m).

module "gateway_targets" {
  for_each = { for idx, t in var.gateway_targets : "${t.gateway}-${idx}" => t }
  source   = "../../modules/gateway-target"

  gateway_identifier = local.gateways_by_name[each.value.gateway]
  name               = "${local.runtime_name}-${each.value.gateway}"
  description        = "Target de ${local.runtime_name} en gateway ${each.value.gateway}"
  target_configuration = {
    mcp = {
      open_api_schema = {
        s3 = {
          uri = each.value.tools_schema_s3_uri
        }
      }
    }
  }
  credential_provider_configurations = []
}
