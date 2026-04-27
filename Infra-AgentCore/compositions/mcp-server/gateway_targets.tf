# Gateway targets — el MCP runtime se expone via Lambda-style target.
# Si hay OAuth provider definido, se asocia como credential provider del target.

module "gateway_targets" {
  for_each = { for idx, t in var.gateway_targets : "${t.gateway}-${idx}" => t }
  source   = "../../modules/gateway-target"

  gateway_identifier = local.gateways_by_name[each.value.gateway]
  name               = "${local.runtime_name}-${each.value.gateway}"
  description        = "MCP target de ${local.runtime_name}"
  target_configuration = {
    mcp = {
      lambda = {
        lambda_arn = module.runtime.agent_runtime_alias_arn
      }
    }
  }
  credential_provider_configurations = length(module.oauth_provider) > 0 ? [{
    oauth = {
      provider_arn = module.oauth_provider[0].credential_provider_arn
      scopes       = []
    }
  }] : []
}
