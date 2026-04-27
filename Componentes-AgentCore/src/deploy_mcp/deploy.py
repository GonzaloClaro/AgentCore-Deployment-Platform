"""deploy_mcp (macro): atajo equivalente a deploy_agent pero para MCP servers."""
from __future__ import annotations

import os


def main() -> int:
    print("[deploy_mcp] macro: re-ejecutar como pasos individuales en el Compose")
    print(f"[deploy_mcp] workload={os.environ.get('WORKLOAD_PATH')} gateway={os.environ.get('GATEWAY')}")
    print("[deploy_mcp] no-op: la orquestación real está en Compose-AgentCore/pipeline_deploy_mcps.yml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
