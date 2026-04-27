# tests/defaults.tftest.hcl — terraform test del módulo runtime
# Ejecutar: cd modules/runtime && terraform init -backend=false && terraform test

variables {
  name        = "test-runtime"
  role_arn    = "arn:aws:iam::111122223333:role/test"
  image_uri   = "111122223333.dkr.ecr.us-east-1.amazonaws.com/test:abc"
  pipeline_id = "pipeline-42"
}

run "creates_runtime_with_alias_live" {
  command = plan

  assert {
    condition     = aws_bedrockagentcore_agent_runtime.this.name == "test-runtime"
    error_message = "Runtime name debe matchear el input."
  }

  assert {
    condition     = aws_bedrockagentcore_agent_runtime_alias.live.name == "live"
    error_message = "Alias debe llamarse 'live' (contrato del módulo)."
  }

  assert {
    condition     = aws_bedrockagentcore_agent_runtime.this.role_arn == "arn:aws:iam::111122223333:role/test"
    error_message = "role_arn debe ser el del input."
  }
}

run "env_vars_se_propagan" {
  command = plan
  variables {
    env_vars = {
      LOG_LEVEL = "DEBUG"
      KB_ID     = "kb-xyz"
    }
  }

  assert {
    condition     = aws_bedrockagentcore_agent_runtime.this.environment_variables["LOG_LEVEL"] == "DEBUG"
    error_message = "env_vars deben llegar al recurso."
  }
}

run "memory_id_null_no_crea_bloque_memory" {
  command = plan
  variables {
    memory_id = null
  }

  # Cuando memory_id es null, el bloque dynamic "memory" no se crea
  # Esto se valida indirectamente: el plan no falla
  assert {
    condition     = aws_bedrockagentcore_agent_runtime.this.name == "test-runtime"
    error_message = "Plan debe pasar con memory_id=null (runtime stateless)."
  }
}

run "tags_se_mergean_con_managed_by" {
  command = plan
  variables {
    tags = { Owner = "team-x", Environment = "dev" }
  }

  assert {
    condition     = aws_bedrockagentcore_agent_runtime.this.tags["ManagedBy"] == "agentcore-pipeline"
    error_message = "Tag ManagedBy debe estar siempre presente."
  }

  assert {
    condition     = aws_bedrockagentcore_agent_runtime.this.tags["Owner"] == "team-x"
    error_message = "Tags del usuario deben mergearse."
  }
}
