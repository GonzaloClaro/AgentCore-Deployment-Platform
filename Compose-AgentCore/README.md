# Compose-AgentCore

> **Tipo:** Orquestación productiva (NO contiene Python ni lógica)
> **Consume:** componentes de `Componentes-AgentCore` vía `include: - component:`

Este repo es el **director de orquesta** de los despliegues AgentCore. Define los pipelines productivos (`pipeline_*.yml`), las reglas de promoción dev/qa/prd, las tags de runners y las variables de ambiente.

## Reglas duras (framework)

- **Solo YAML**, cero Python.
- Aquí SÍ van `rules`, `tags`, `default:`, `stages`, `environment`, `extends`.
- Todo job que ejecuta lógica viene de un `include: - component:` de `Componentes-AgentCore`.
- Variables sensibles (tokens, ARNs de roles) NUNCA hardcodeadas; vienen de CI/CD variables protegidas con scope=`environment`.

## Pipelines

| Pipeline | Consumido por | Propósito |
|---|---|---|
| `pipeline_deploy_agents.yml` | `AgentPlatform/.gitlab-ci.yml` | Despliega un agente cuando hay cambios en `agents/**` |
| `pipeline_deploy_mcps.yml` | `AgentPlatform/.gitlab-ci.yml` | Despliega un MCP server cuando hay cambios en `mcp/**` |
| `pipeline_infra.yml` | `iac/AgentCore/agentcore-{dev,qa,prd}/.gitlab-ci.yml` | Pipeline downstream que ejecuta Terraform |
| `pipeline_foundation.yml` | `Infra-AgentCore/.gitlab-ci.yml` (cuando cambian `foundation/**`) | Bootstrap por cuenta + 3 default gateways |
| `pipeline_catalog.yml` | `AgentPlatform/.gitlab-ci.yml` (solo branch main) | Publica metadata de manifests a LeanIX |

## Estructura

```
pipeline_deploy_agents.yml
pipeline_deploy_mcps.yml
pipeline_infra.yml
pipeline_foundation.yml
pipeline_catalog.yml
rules/
  branch-to-env.yml         # mapea branch → environment + role_arn
  paths.yml                 # rules de cambios por path (agents/**, mcp/**)
  approvals.yml             # required approvals para qa/prd
variables/
  env-dev.yml               # IMAGE_BASE, S3_BUCKET pattern, AWS_ROLE_ARN para dev
  env-qa.yml
  env-prd.yml
```

## Versionado

- `main` = productivo
- Pinear desde el consumidor: `include: - project: Componentes/Compose/agentcore, file: pipeline_deploy_agents.yml, ref: v1.x.y`
