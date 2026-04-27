provider "aws" {
  region = "us-east-1"

  assume_role {
    role_arn     = var.aws_role_arn
    session_name = "agentcore-qa-${var.workload_name}"
  }

  default_tags {
    tags = {
      Environment = "qa"
      Domain      = "agentcore"
      ManagedBy   = "agentcore-pipeline"
    }
  }
}

variable "aws_role_arn" {
  type = string
}

variable "workload_name" {
  type    = string
  default = "deploy"
}
