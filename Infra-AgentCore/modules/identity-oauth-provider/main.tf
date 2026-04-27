# modules/identity-oauth-provider
# Crea un OAuth2 credential provider para AgentCore Identity con vendor=CustomOauth2.
# El client_secret se lee de Secrets Manager y se pasa al provider via client_secret.
#
# CAVEAT seguridad: en provider 6.x el client_secret se pasa en plano (terminará en el
# state file). Para mitigarlo, mover a `client_secret_wo` (write-only) cuando se confirme
# Terraform >= 1.11 en el runner. El recurso ya no acepta secret_arn como input.

data "aws_secretsmanager_secret_version" "client_secret" {
  secret_id = var.client_secret_arn
}

resource "aws_bedrockagentcore_oauth2_credential_provider" "this" {
  name                       = var.name
  credential_provider_vendor = "CustomOauth2"

  oauth2_provider_config {
    custom_oauth2_provider_config {
      client_id     = var.client_id
      client_secret = data.aws_secretsmanager_secret_version.client_secret.secret_string

      oauth_discovery {
        authorization_server_metadata {
          authorization_endpoint = var.authorization_endpoint
          token_endpoint         = var.token_endpoint
          issuer                 = var.issuer
          response_types         = ["code"]
        }
      }
    }
  }
}
