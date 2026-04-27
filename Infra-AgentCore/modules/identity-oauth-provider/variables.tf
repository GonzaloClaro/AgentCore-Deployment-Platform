variable "name" { type = string }
variable "client_id" { type = string }
variable "client_secret_arn" {
  type        = string
  description = "ARN del secreto en Secrets Manager con el client_secret"
}
variable "issuer" { type = string }
variable "authorization_endpoint" { type = string }
variable "token_endpoint" { type = string }
