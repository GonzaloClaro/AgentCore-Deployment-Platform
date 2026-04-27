# Targets que referencian recursos PRE-EXISTENTES (Lambdas, OpenAPI schemas).
# El dev declara en el manifest:
#   gateway_targets:
#     - name: existing-tool-1
#       target_kind: lambda           # lambda | open_api | smithy
#       target_arn: "arn:aws:lambda:..:tool-X"   # para lambda
#     - name: existing-tool-2
#       target_kind: open_api
#       target_s3_uri: "s3://my-bucket/schema.yaml"

module "targets" {
  for_each = { for idx, t in var.gateway_targets : t.name => t }
  source   = "../../modules/gateway-target"

  gateway_identifier = module.gateway.gateway_id
  name               = each.value.name
  description        = lookup(each.value, "description", "Target ${each.value.name} en ${local.gateway_name}")
  target_configuration = each.value.target_kind == "lambda" ? {
    mcp = { lambda = { lambda_arn = each.value.target_arn } }
    } : each.value.target_kind == "open_api" ? {
    mcp = { open_api_schema = { s3 = { uri = each.value.target_s3_uri } } }
    } : {
    mcp = { smithy_model = { s3 = { uri = each.value.target_s3_uri } } }
  }
  credential_provider_configurations = lookup(each.value, "credential_provider_configurations", [])
}
