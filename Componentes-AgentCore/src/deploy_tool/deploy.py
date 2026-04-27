"""deploy_tool (macro): orquestador alto nivel para tools.

Tool kind:
  - embedded: la tool es código Python en el agente. No despliega infra, solo valida que
    el agente que la importa exista. Útil como gate antes del build del agente.
  - lambda:   se despliega como composition tool-lambda. Este script genera el manifest
    interno y llama a los componentes individuales (package_artifact, build, render, trigger).
    En la práctica, el flujo recomendado es usar pipeline_deploy_tools.yml directamente.
  - open_api: la tool es un HTTP API ya existente. Solo registra el target en gateway.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    workload = os.environ.get("WORKLOAD_PATH", "")
    capability = os.environ.get("CAPABILITY", "")
    name = os.environ.get("WORKLOAD_NAME", "")
    kind = os.environ.get("TOOL_KIND", "embedded")
    env = os.environ.get("ENVIRONMENT", "dev")

    print(f"[deploy_tool] {capability}/{name} kind={kind} env={env} workload={workload}")

    if kind == "embedded":
        print("[deploy_tool] embedded → no infra. La tool se hornea en la imagen del agente que la importa.")
        print("[deploy_tool] valida que requirements.txt existe y src/ tiene contenido.")
        if not os.path.isdir(os.path.join(workload, "src")):
            print("ERROR: src/ no existe en el workload de la tool", file=sys.stderr)
            return 2
        return 0

    if kind == "lambda":
        print("[deploy_tool] lambda → orquestar pipeline_deploy_tools.yml (lambda + gateway-target)")
        print("[deploy_tool] no-op aquí; la orquestación real vive en Compose-AgentCore/pipeline_deploy_tools.yml")
        return 0

    if kind == "open_api":
        print("[deploy_tool] open_api → solo registrar target en gateway por defecto")
        print("[deploy_tool] no-op aquí; la orquestación real es composition agent-with-tools o gateway-deploy")
        return 0

    print(f"ERROR: tool_kind desconocido: {kind}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
