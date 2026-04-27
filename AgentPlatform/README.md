# AgentPlatform

> **Tipo:** Repo de workloads (agentes, MCP servers, tools)
> **Branching:** `dev` → `qa` → `main` (con tags semver para PRD)

Aquí viven el código y los manifiestos de los agentes, MCP servers y tools de los equipos. **Cada workload se despliega solo cuando se modifican archivos bajo su path** — el pipeline detecta cambios y dispara despliegues granulares.

## Estructura

```
agents/
  {capability}/                       # ej: customer-support, finance, hr
    {name}/                           # ej: chatbot-tier1
      manifest.yaml                   # ⭐ contrato declarativo opinado
      src/
        agent.py                      # entrypoint del agente
        requirements.txt
        Dockerfile                    # opcional, override del default
      prompts/
        system_prompt.yaml
      kb/
        data_sources.yaml             # rutas S3 a indexar (no datos)
mcp/
  {capability}/{name}/                # estructura idéntica, composition: mcp-server
tools/                                # libs Python compartidas
.gitlab-ci.yml                        # trigger al Compose-AgentCore
```

## Cómo agregar un nuevo agente

1. Copia `agents/_template/` a `agents/<tu-capability>/<tu-nombre>/`.
2. Edita `manifest.yaml`:
   - `metadata.name`, `metadata.capability`, `metadata.owner`.
   - `spec.composition`: elige una de `agent-chatbot | agent-with-kb | agent-with-tools | mcp-server | agent-full`.
   - Habilita features según necesites.
3. Implementa `src/agent.py` exponiendo un `app` (FastAPI/uvicorn) con endpoints `/invocations` y `/ping`.
4. (Opcional) Agrega prompts en `prompts/*.yaml` — se versionan automáticamente en Bedrock Prompt Management.
5. (Opcional) Define KB sources en `kb/data_sources.yaml`.
6. Push a branch `dev` → pipeline despliega en cuenta DEV.
7. MR `dev` → `qa` (manual approval) → `qa` → `main` con tag `vX.Y.Z` para PRD.

## Manifest opinado

Ver `agents/_template/manifest.yaml` y el JSON-schema en `Componentes-AgentCore/config_files/validate_manifest/manifest.schema.json`.

## Promoción

| Branch | Cuenta AWS | Aprobación |
|---|---|---|
| `dev` | dev-agenticplatform | automática |
| `qa` | qa-agenticplatform | manual approval |
| `main` + tag `vX.Y.Z` | prd-agenticplatform | manual approval |

## Rollback

Cada apply produce una versión inmutable del runtime y un alias `live`. Para hacer rollback:

```bash
# Editar el manifest para apuntar a versión previa
spec:
  runtime:
    target_version: "3"   # versión a la que se quiere volver
```

Push y apply mueve el alias `live` sin downtime.
