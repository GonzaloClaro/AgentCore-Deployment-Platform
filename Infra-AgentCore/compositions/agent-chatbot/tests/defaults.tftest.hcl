# tests/defaults.tftest.hcl — composition agent-chatbot
# Valida que el role efectivo es default si no hay runtime_iam, y custom si se declara.

variables {
  name             = "test"
  capability       = "sandbox"
  environment      = "dev"
  default_role_arn = "arn:aws:iam::111122223333:role/default-shared"
  image_uri        = "111122223333.dkr.ecr.us-east-1.amazonaws.com/test:abc"
  runtime          = { entrypoint = "agent.py", env = {} }
  memory           = { strategy = "summarization" }
}

run "sin_runtime_iam_usa_default_role_arn" {
  command = plan

  assert {
    condition     = local.has_runtime_iam == false
    error_message = "Sin runtime_iam, has_runtime_iam debe ser false."
  }

  assert {
    condition     = local.effective_runtime_role_arn == "arn:aws:iam::111122223333:role/default-shared"
    error_message = "Sin runtime_iam, effective role debe ser el default."
  }
}

run "con_managed_policy_crea_role_custom" {
  command = plan
  variables {
    runtime_iam = {
      managed_policy_arns = ["arn:aws:iam::111122223333:policy/managed-x"]
      inline_policies     = []
    }
  }

  assert {
    condition     = local.has_runtime_iam == true
    error_message = "Declarar managed_policy_arns debe activar el role custom."
  }

  assert {
    condition     = length(module.runtime_role) == 1
    error_message = "module.runtime_role debe instanciarse 1 vez."
  }
}

run "memory_strategy_none_no_crea_strategies" {
  command = plan
  variables {
    memory = { strategy = "none" }
  }

  # Sin strategies → el for_each de aws_bedrockagentcore_memory_strategy es vacío
  assert {
    condition     = length(module.memory.strategies) == 0
    error_message = "memory.strategy='none' debe resultar en 0 strategies."
  }
}
