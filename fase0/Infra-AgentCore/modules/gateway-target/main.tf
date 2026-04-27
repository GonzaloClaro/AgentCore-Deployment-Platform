# modules/gateway-target
# Agrega un target a un gateway existente (típicamente uno de los 3 default).
# Provider 6.x soporta el recurso nativo con grant_type para OAuth (issue #46128 cerrado).
# El workaround con aws-cli/local-exec que existía antes ya no es necesario.

resource "aws_bedrockagentcore_gateway_target" "this" {
  gateway_identifier = var.gateway_identifier
  name               = var.name
  description        = var.description

  target_configuration {
    dynamic "mcp" {
      for_each = try(var.target_configuration.mcp, null) != null ? [var.target_configuration.mcp] : []
      content {
        dynamic "lambda" {
          for_each = try(mcp.value.lambda, null) != null ? [mcp.value.lambda] : []
          content {
            lambda_arn = lambda.value.lambda_arn
          }
        }

        dynamic "open_api_schema" {
          for_each = try(mcp.value.open_api_schema, null) != null ? [mcp.value.open_api_schema] : []
          content {
            dynamic "s3" {
              for_each = try(open_api_schema.value.s3, null) != null ? [open_api_schema.value.s3] : []
              content {
                uri                     = s3.value.uri
                bucket_owner_account_id = try(s3.value.bucket_owner_account_id, null)
              }
            }
            dynamic "inline_payload" {
              for_each = try(open_api_schema.value.inline_payload, null) != null ? [open_api_schema.value.inline_payload] : []
              content {
                payload = inline_payload.value.payload
              }
            }
          }
        }

        dynamic "smithy_model" {
          for_each = try(mcp.value.smithy_model, null) != null ? [mcp.value.smithy_model] : []
          content {
            dynamic "s3" {
              for_each = try(smithy_model.value.s3, null) != null ? [smithy_model.value.s3] : []
              content {
                uri                     = s3.value.uri
                bucket_owner_account_id = try(s3.value.bucket_owner_account_id, null)
              }
            }
            dynamic "inline_payload" {
              for_each = try(smithy_model.value.inline_payload, null) != null ? [smithy_model.value.inline_payload] : []
              content {
                payload = inline_payload.value.payload
              }
            }
          }
        }
      }
    }
  }

  dynamic "credential_provider_configuration" {
    for_each = var.credential_provider_configurations
    content {
      dynamic "oauth" {
        for_each = try(credential_provider_configuration.value.oauth, null) != null ? [credential_provider_configuration.value.oauth] : []
        content {
          provider_arn = oauth.value.provider_arn
          scopes       = try(oauth.value.scopes, [])
          grant_type   = try(oauth.value.grant_type, null)
        }
      }
      dynamic "gateway_iam_role" {
        for_each = try(credential_provider_configuration.value.gateway_iam_role, null) != null ? [1] : []
        content {}
      }
      dynamic "api_key" {
        for_each = try(credential_provider_configuration.value.api_key, null) != null ? [credential_provider_configuration.value.api_key] : []
        content {
          provider_arn              = api_key.value.provider_arn
          credential_location       = try(api_key.value.credential_location, null)
          credential_parameter_name = try(api_key.value.credential_parameter_name, null)
          credential_prefix         = try(api_key.value.credential_prefix, null)
        }
      }
    }
  }
}
