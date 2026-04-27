# tests/defaults.tftest.hcl — runtime-role module
# Valida: role creado, attach_bedrock_invoke por default, managed + inline policies.

variables {
  runtime_name = "test-rt"
}

run "role_default_attacha_bedrock_invoke" {
  command = plan

  assert {
    condition     = aws_iam_role.runtime.name == "test-rt-execution"
    error_message = "Role name debe seguir patrón <runtime_name>-execution."
  }

  assert {
    condition     = length([for k, v in aws_iam_role_policy.bedrock_invoke : v]) > 0
    error_message = "attach_bedrock_invoke=true por default debe crear el inline policy."
  }
}

run "managed_policy_arns_se_attachan" {
  command = plan
  variables {
    managed_policy_arns = [
      "arn:aws:iam::111122223333:policy/managed-1",
      "arn:aws:iam::111122223333:policy/managed-2",
    ]
  }

  assert {
    condition     = length(aws_iam_role_policy_attachment.managed) == 2
    error_message = "Se debe crear 1 attachment por cada managed_policy_arn."
  }
}

run "inline_policies_se_crean_con_nombre_correcto" {
  command = plan
  variables {
    inline_policies = [
      {
        name            = "read-bucket"
        policy_document = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = "s3:GetObject", Resource = "*" }] })
      }
    ]
  }

  assert {
    condition     = aws_iam_role_policy.inline["read-bucket"].name == "read-bucket"
    error_message = "Inline policy debe crearse con el name del input."
  }
}

run "attach_bedrock_invoke_false_no_crea_policy" {
  command = plan
  variables {
    attach_bedrock_invoke = false
  }

  assert {
    condition     = length(aws_iam_role_policy.bedrock_invoke) == 0
    error_message = "attach_bedrock_invoke=false NO debe crear el bedrock policy."
  }
}

run "permissions_boundary_se_aplica_si_se_provee" {
  command = plan
  variables {
    permissions_boundary_arn = "arn:aws:iam::111122223333:policy/CorpBoundary"
  }

  assert {
    condition     = aws_iam_role.runtime.permissions_boundary == "arn:aws:iam::111122223333:policy/CorpBoundary"
    error_message = "permissions_boundary del input debe llegar al role."
  }
}
