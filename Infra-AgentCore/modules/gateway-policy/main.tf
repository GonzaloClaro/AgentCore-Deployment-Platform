# modules/gateway-policy
# Crea un Policy Engine Cedar y lo asocia a un Gateway AgentCore.
#
# Estado del provider AWS Terraform (verificado abril 2026):
#   - aws_bedrockagentcore_policy_engine NO existe
#   - aws_bedrockagentcore_policy        NO existe
# Workaround: null_resource + local-exec usando la CLI oficial `agentcore`.
# Cuando salga el resource nativo en hashicorp/aws, switchear con use_native_resource=true.
#
# La CLI `agentcore` es la herramienta oficial (no `aws bedrock-agentcore-control`).
# Comandos relevantes:
#   agentcore add policy-engine --name <name> --attach-to-gateways <gateway-name> --attach-mode ENFORCE|LOGONLY
#   agentcore add policy --name <policy-name> --engine <engine-name> --source <file.cedar>
#   agentcore remove policy-engine --name <name>
#   agentcore status
#
# Modos:
#   - ENFORCE  → bloquea (default deny + forbid wins)
#   - LOGONLY  → observa y loggea decisiones sin bloquear (modo "shadow", recomendado al inicio)

resource "null_resource" "policy_engine" {
  triggers = {
    gateway_name      = var.gateway_name
    engine_name       = var.name
    attach_mode       = var.attach_mode
    policies_checksum = sha256(join("\n", var.cedar_policies))
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      echo "[gateway-policy] policy engine '${var.name}' → gateway '${var.gateway_name}' (mode=${var.attach_mode})"

      # Idempotente: si ya existe, lo removemos y recreamos (necesario para cambiar attach_mode)
      agentcore remove policy-engine --name ${var.name} 2>/dev/null || true

      agentcore add policy-engine \
        --name ${var.name} \
        --attach-to-gateways ${var.gateway_name} \
        --attach-mode ${var.attach_mode}

      # Cargar cada policy Cedar como archivo y agregar al engine
      mkdir -p /tmp/cedar-${var.name}
      ${join("\n", [
    for idx, policy in var.cedar_policies :
    "cat > /tmp/cedar-${var.name}/policy-${idx}.cedar <<'CEDAR_EOF'\n${policy}\nCEDAR_EOF\nagentcore add policy --name policy-${idx} --engine ${var.name} --source /tmp/cedar-${var.name}/policy-${idx}.cedar"
])}

      agentcore deploy
      echo "[gateway-policy] deploy ok (${length(var.cedar_policies)} policies, mode=${var.attach_mode})"
    EOT
}

provisioner "local-exec" {
  when    = destroy
  command = "agentcore remove policy-engine --name ${self.triggers.engine_name} && agentcore deploy || true"
}
}
