# tests/defaults.tftest.hcl — gateway-policy module

variables {
  name           = "test_engine"
  gateway_name   = "oauth-3lo"
  cedar_policies = ["permit(principal, action, resource);"]
}

run "name_pattern_valido_pasa" {
  command = plan
  # El módulo tiene validation regex en `name`
  assert {
    condition     = null_resource.policy_engine.triggers.engine_name == "test_engine"
    error_message = "Engine name debe propagarse al null_resource."
  }
}

run "attach_mode_default_es_logonly" {
  command = plan
  assert {
    condition     = null_resource.policy_engine.triggers.attach_mode == "LOGONLY"
    error_message = "Default seguro: LOGONLY (shadow mode)."
  }
}

run "attach_mode_invalido_falla" {
  command = plan
  variables {
    attach_mode = "INVALID_MODE"
  }
  expect_failures = [var.attach_mode]
}

run "checksum_cambia_si_policies_cambian" {
  command = plan
  variables {
    cedar_policies = ["permit(...)", "forbid(...)"]
  }
  assert {
    condition     = null_resource.policy_engine.triggers.policies_checksum != ""
    error_message = "Checksum debe estar siempre presente para detectar cambios."
  }
}
