# OAuth2 credential provider — solo se crea si se proveen credenciales en var.oauth_provider.
# El client_secret_arn debe venir del componente CI upload_secret (Secrets Manager).

module "oauth_provider" {
  count  = var.oauth_provider != null ? 1 : 0
  source = "../../modules/identity-oauth-provider"

  name                   = "${local.runtime_name}-oauth"
  client_id              = var.oauth_provider.client_id
  client_secret_arn      = var.oauth_provider.client_secret_arn
  issuer                 = var.oauth_provider.issuer
  authorization_endpoint = var.oauth_provider.authorization_endpoint
  token_endpoint         = var.oauth_provider.token_endpoint
}
