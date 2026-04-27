terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.70"
    }
  }
  # Backend HTTP (GitLab managed state) — los parámetros vienen de -backend-config en init.
  backend "http" {}
}
