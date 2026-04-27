# AgentPlatform (fase 0)

Repo de workloads en versión MVP. Solo agentes (sin MCP, sin tools).

## Cómo agregar un agente

1. Copiá `agents/_template/` a `agents/<capability>/<nombre>/`
2. Editá `manifest.yaml` con tus valores
3. Implementá `src/main.py` con `/ping` y `/invocations`
4. `git push` a branch `dev` → pipeline despliega automáticamente

## Restricciones de fase 0

- **Solo zip** (no container/Docker)
- **Solo Python** (`PYTHON_3_13`) — el runtime AgentCore arranca `python <entrypoint>`
- **2 composiciones disponibles**: `agent-base-zip` y `agent-with-kb-zip`
- **Sin tools/gateways** — el agente es self-contained
- **Sin MCP server** — solo agentes invocables

## Estructura

```
agents/
  <capability>/<nombre>/
    manifest.yaml         # contrato declarativo
    src/
      main.py             # entrypoint (HTTP server en :8080)
      requirements.txt
    prompts/              # opcional: prompts/<nombre>.yaml
```

Ver `docs/resumen.md` (raíz del repo) para el flujo completo del pipeline.
