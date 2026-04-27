provider "aws" {
  region = "us-east-1"

  assume_role {
    role_arn     = var.aws_role_arn
    session_name = "agentcore-dev-${var.workload_name}"
  }

  default_tags {
    tags = {
      Environment = "dev"
      Domain      = "agentcore"
      ManagedBy   = "agentcore-pipeline"
    }
  }
}

variable "aws_role_arn" {
  type        = string
  description = "Role IAM en cuenta DEV asumido por el pipeline"
}

variable "workload_name" {
  type        = string
  description = "Nombre del workload (para session name)"
  default     = "deploy"
}
