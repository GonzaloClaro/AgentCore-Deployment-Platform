variable "name" { type = string }
variable "allowed_oauth_return_urls" {
  type    = list(string)
  default = []
}
