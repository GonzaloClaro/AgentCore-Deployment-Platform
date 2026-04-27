"""deploy_agent (macro): atajo simple que reusa los componentes individuales.

Para flujos productivos completos preferir incluir cada componente
(validate_manifest, package_artifact, build_image, render_tfvars, trigger_iac)
en el pipeline del Compose. Este script existe para debug local y prototipos.
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    print("[deploy_agent] macro: re-ejecutar como pasos individuales en el Compose")
    print(f"[deploy_agent] workload={os.environ.get('WORKLOAD_PATH')} env={os.environ.get('ENVIRONMENT')}")
    print("[deploy_agent] no-op: la orquestación real está en Compose-AgentCore/pipeline_deploy_agents.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
