# Índice y Glosario

> Mapa de **dónde vive cada cosa** + glosario de **qué significa cada término**. La primera parada cuando uno se pierde en el repo.

## Índice de archivos relevantes

### Raíz del proyecto

| Archivo | Para qué sirve | Cuándo lo abro |
|---|---|---|
| `PLAN.md` | Plan original aprobado del proyecto | Onboarding, contexto histórico |
| `MANIFEST_REFERENCE.md` | Referencia exhaustiva de todos los campos del `manifest.yaml` (y validaciones, mapping a TF, secciones por capability) | Cuando dudo qué puedo configurar en un manifest |
| `CI_VARIABLES.md` | Lista de variables CI/CD por GitLab group + bootstrap checklist | Configurando GitLab por primera vez o agregando shard nuevo |
| `MULTI_ACCOUNT.md` | Estrategia de account sharding + cómo agregar cuenta nueva | Cuando se llena la quota de una cuenta |
| `RUNBOOK_DESTROY_PRD.md` | Cómo destruir recursos en PRD con compliance | Caso excepcional de descontinuación de workload |
| `.env.example` | Plantilla local de variables para desarrollo | Setup inicial de máquina dev |
| `.gitignore` | Excluye `.env`, `.terraform/`, `*.tfstate`, artifacts | Convención |

### Carpeta `docs/`

| Archivo | Para qué sirve |
|---|---|
| `docs/01_IMPROVEMENTS_AND_FUTURE_WORK.md` | Roadmap de mejoras, priorizado por disparadores |
| `docs/02_PHASED_IMPLEMENTATION_PLAN.md` | Plan de implementación incremental por fases (0-9+) |
| `docs/03_INDEX_GLOSSARY.md` | Este archivo |
| `docs/04_ARCHITECTURE_COMPONENTS.md` | Cómo funcionan los componentes CI, compose, módulos TF, composiciones |
| `docs/05_FLOWS_AND_DIAGRAMS.md` | Flujos end-to-end con diagramas Mermaid |
| `docs/06_EXECUTIVE_OVERVIEW.md` | Documento ejecutivo: por qué este enfoque + compromisos por área |
| `docs/07_QUOTAS.md` | Quotas de AgentCore, escenarios de saturación, mitigaciones |

### Repositorios principales

#### `Componentes-AgentCore/`
> Componentes CI reutilizables (templates YAML + scripts Python).

| Path | Para qué sirve |
|---|---|
| `README.md` | Descripción del repo, reglas duras del framework |
| `templates/<subdominio>/template.yml` | Componente CI publicable (consumido vía `include: - component:`) |
| `src/<subdominio>/<action>.py` | Lógica Python ejecutada por el componente |
| `src/utils/{aws_client,manifest_parser,gitlab_client,telemetry}.py` | Helpers compartidos entre componentes |
| `config_files/allowed_models.yml` | ⭐ **Whitelist gobernada de modelos LLM permitidos** |
| `config_files/validate_manifest/manifest.schema.json` | ⭐ **JSON-schema del manifest opinado (contrato dev↔plataforma)** |
| `config_files/render_tfvars/composition_map.yml` | Mapping composition → módulos TF (validación cruzada) |
| `config_files/build_image/agent-runtime.Dockerfile` | Dockerfile base ARM64 para agentes |
| `config_files/build_image/mcp-server.Dockerfile` | Dockerfile base ARM64 para MCP servers |
| `tests/unit/*.py` | Tests pytest del repo |

**Subdominios (componentes CI):**

| Subdominio | Propósito |
|---|---|
| `validate_manifest` | Valida `manifest.yaml` contra JSON-schema |
| `validate_structure` | Validación cruzada (composition existe, archivos referenciados, alias unique, etc.) |
| `package_artifact` | Zip del workload + upload S3 |
| `build_image` | Docker buildx ARM64 + push ECR |
| `scan_image` | Trivy/Inspector con gate por severity |
| `upload_secret` | CI variable masked → AWS Secrets Manager |
| `publish_prompt` | YAMLs de prompts → Bedrock Prompt Mgmt (SDK, versionado nativo) |
| `apply_policy` | Lee `.cedar` files → `cedar_policies.json` |
| `render_tfvars` | manifest + env-defaults + intermediate outputs → `terraform.auto.tfvars.json` |
| `trigger_iac` | Multi-project pipeline trigger al deployable |
| `smoke_test` | Invoca `/ping` del runtime post-apply |
| `publish_leanix` | Manifests → fact sheets LeanIX |
| `pipeline_telemetry` | Genera/propaga TRACE_ID, emite eventos a CloudWatch |
| `drift_check` | Analiza `terraform plan -json` y categoriza severidad |
| `deploy_agent` / `deploy_mcp` / `deploy_tool` | Macros (atajos) — no usar en flujo prod |

#### `Compose-AgentCore/`
> Orquestación productiva (YAML, sin Python).

| Path | Para qué sirve |
|---|---|
| `pipeline_deploy_agents.yml` | ⭐ **Pipeline completo de despliegue de agente** |
| `pipeline_deploy_agents_minimal.yml` | Variante reducida para Fase 1 (sin telemetry/structure/policy) |
| `pipeline_deploy_mcps.yml` | Pipeline de despliegue de MCP server |
| `pipeline_infra.yml` | Pipeline downstream que ejecuta Terraform en `agentcore-{env}` |
| `pipeline_foundation.yml` | Bootstrap por cuenta + 3 default gateways |
| `pipeline_drift_detection.yml` | Drift detection scheduled (nightly cron) |
| `pipeline_infra_tests.yml` | Tests del repo Infra-AgentCore (validate, fmt, terraform test) |
| `pipeline_catalog.yml` | Publica metadata a LeanIX (solo branch main) |
| `rules/branch-to-env.yml` | Mapping `dev`/`qa`/`main` → `ENVIRONMENT` + `AWS_ROLE_ARN` |
| `rules/paths.yml` | Rules de cambios por path (`agents/**`, `mcp/**`, etc.) |
| `rules/approvals.yml` | Manual gates QA/PRD |
| `variables/env-{dev,qa,prd}.yml` | Defaults por ambiente (image, S3 buckets, ECR registry) |

#### `Infra-AgentCore/`
> Código Terraform: módulos + composiciones (sin state).

| Path | Para qué sirve |
|---|---|
| `README.md` | Patrón módulos vs composiciones, cómo crear composition custom |
| `modules/<nombre>/{main,variables,outputs,versions}.tf` | Módulo TF reusable de un solo recurso/componente |
| `compositions/<nombre>/{main,<componente>.tf,variables,outputs}.tf` | Composición que ensambla módulos para un arquetipo |
| `foundation/bootstrap/main.tf` | Aplicado UNA VEZ por cuenta — KMS, S3 buckets, IAM, IAM deny PRD, emergency destroyer |
| `foundation/default-gateways/main.tf` | Los 3 gateways por defecto del ambiente (3LO, 2LO, SigV4) |
| `foundation/vpc-endpoints/main.tf` | Endpoints VPC privados (Bedrock, S3, ECR, Secrets) |
| `tests/README.md` | Cómo correr tests Terraform por nivel |
| `modules/<m>/tests/*.tftest.hcl` | Tests del módulo con `command = plan` |

**Módulos TF (11):**

| Módulo | Recurso AWS |
|---|---|
| `runtime` | `aws_bedrockagentcore_agent_runtime` + version + alias `live` |
| `runtime-role` | `aws_iam_role` per-workload con managed/inline policies |
| `memory` | `aws_bedrockagentcore_memory` + memory_strategy |
| `observability` | CloudWatch log group + X-Ray sampling + dashboard |
| `knowledge-base` | `aws_bedrockagent_knowledge_base` + `aws_s3vectors_*` |
| `gateway` | `aws_bedrockagentcore_gateway` (uso casi exclusivo en foundation) |
| `gateway-target` | `aws_bedrockagentcore_gateway_target` (con workaround #46128) |
| `gateway-policy` | Policy Engine Cedar via CLI `agentcore` (workaround `null_resource`) |
| `identity-oauth-provider` | `aws_bedrockagentcore_oauth2_credential_provider` |
| `lambda-tool` | `aws_lambda_function` ARM64 + role |
| `workload-identity` | `aws_bedrockagentcore_workload_identity` (avanzado) |

**Composiciones (7):**

| Composición | Módulos que ensambla | Caso de uso |
|---|---|---|
| `agent-base` | runtime + observability | Agente stateless (clasificador, traductor) |
| `agent-chatbot` | + memory | Chatbot simple |
| `agent-with-kb` | + knowledge-base | Agente con RAG |
| `agent-with-tools` | + gateway-target | Agente con tools externas |
| `mcp-server` | runtime + oauth-provider + gateway-target | MCP server con OAuth |
| `tool-lambda` | lambda-tool + gateway-target | Tool standalone como Lambda |
| `gateway-deploy` | gateway + targets + policies | Gateway custom (raro, casi nunca) |

#### `AgentPlatform/`
> Workloads (agentes, MCP servers, tools).

| Path | Para qué sirve |
|---|---|
| `.gitlab-ci.yml` | Trigger al pipeline del Compose |
| `agents/{capability}/{name}/manifest.yaml` | ⭐ **Manifest opinado del workload** |
| `agents/{capability}/{name}/src/agent.py` | Código Python del agente (FastAPI) |
| `agents/_template/` | ⭐ Plantilla para crear agente nuevo |
| `agents/_template/src/agent.py` | ⭐ **Pattern estándar de uso de modelos via env vars** |
| `mcp/{capability}/{name}/` | MCP servers |
| `tools/_template_embedded/` | Plantilla tool embedded (Python lib) |
| `tools/_template_lambda/` | Plantilla tool desplegada como Lambda |

#### `iac/AgentCore/`
> Deployables Terraform (slim, con tfvars + state GitLab).

| Path | Para qué sirve |
|---|---|
| `infra-agentcore/` | Subdir/ref al repo `Infra-AgentCore` (módulos + compositions, sin state) |
| `agentcore-dev/`, `agentcore-qa/`, `agentcore-prd/` | Deployables por cuenta — env-defaults.yaml + .gitlab-ci.yml |
| `agentcore-prd-shard-{a,b,c}/` | Deployables adicionales si se necesita sharding |

---

## Glosario

| Término | Definición |
|---|---|
| **Componente CI** | Template YAML reusable de GitLab (`spec.inputs` + `---`) que define un job genérico. Vive en `Componentes-AgentCore/templates/<subdominio>/template.yml`. La lógica Python vive en `src/<subdominio>/<action>.py`. |
| **Compose** | Pipeline productivo (YAML) que orquesta múltiples componentes con `rules`, `tags`, `stages`, `needs`. Vive en `Compose-AgentCore/pipeline_*.yml`. **No tiene Python.** |
| **Workload** | Una unidad desplegable: un agente, un MCP server, o una tool. Vive en `AgentPlatform/{agents,mcp,tools}/{capability}/{name}/`. |
| **Manifest** | Archivo `manifest.yaml` declarativo en el workload. Validado contra `manifest.schema.json`. Es el **contrato dev↔plataforma**. |
| **Capability** | Agrupación lógica de agentes/MCPs/tools por dominio funcional. Ej: `customer-support`, `finance`, `fraud`. Lista cerrada (definida por arquitectura). |
| **Composition** | Composición Terraform: ensamble de módulos TF para un arquetipo. Vive en `Infra-AgentCore/compositions/<nombre>/` con un `.tf` por módulo enchufado. |
| **Módulo TF** | Pieza atómica reusable de Terraform (1 recurso o componente AgentCore). Vive en `Infra-AgentCore/modules/<nombre>/`. |
| **Foundation** | Recursos AWS que existen una sola vez por cuenta (KMS, S3 buckets, IAM base, default gateways). Vive en `Infra-AgentCore/foundation/`. |
| **Deployable** | Proyecto GitLab slim por cuenta AWS (`agentcore-{env}`) que ejecuta Terraform con state propio (GitLab managed) y env-defaults. Vive en `iac/AgentCore/`. |
| **Shard** | Cuenta AWS adicional dentro de un mismo ambiente cuando una sola cuenta llega a sus quotas. Ej: `prd-shard-a`, `prd-shard-b`. |
| **Env-defaults** | Archivo `env-defaults.yaml` en cada deployable con valores específicos del ambiente (account_id, VPC, KMS, default_role_arn, gateway_ids). |
| **Whitelist (allowed_models)** | Lista cerrada de modelos LLM permitidos por la organización, con scope por ambiente. Cambios = PR auditable. |
| **Cedar policy** | Policy de autorización fine-grained en Cedar language, attached a un Policy Engine asociado a un gateway. **Distinto a IAM**: controla qué tools puede invocar cada principal. |
| **TRACE_ID** | Identificador único generado al inicio del pipeline upstream y propagado a todos los stages + downstream pipelines. Permite correlación end-to-end en CloudWatch. |
| **`alias` de modelo** | Nombre del set de env vars que produce un modelo declarado en `spec.models[]`. Ej: `alias: PRIMARY_MODEL` → env vars `PRIMARY_MODEL_ID`, `PRIMARY_MODEL_PROVIDER`, etc. |
| **`alias` de prompt** | Nombre del env var que recibirá el ARN versionado del prompt en runtime. Ej: `alias: SYSTEM_PROMPT_ARN`. |
| **Default gateway** | Uno de los 3 gateways AgentCore que el ambiente provisiona por defecto: `oauth-3lo` (human-machine), `oauth-2lo` (machine-machine OAuth), `sigv4-m2m` (machine-machine SigV4). |
| **Inference profile** | Recurso AWS Bedrock que provee throughput cross-region garantizado para un modelo. Identificado por ARN. Alternativa al `model_id` directo. |
| **LOGONLY vs ENFORCE** | Modos de attach de un policy engine Cedar. LOGONLY observa decisiones sin bloquear (shadow mode); ENFORCE bloquea. Empezar siempre LOGONLY. |
| **TRACE_ID cross-pipeline** | Mecanismo por el que el TRACE_ID generado en pipeline upstream (workload) se propaga al downstream (deployable infra), permitiendo ver el flujo end-to-end con un solo ID. |

## Mapeo "quiero hacer X → archivo Y"

| Quiero... | Archivo a editar |
|---|---|
| Agregar un agente nuevo | `AgentPlatform/agents/{capability}/{name}/manifest.yaml` (copiar de `_template/`) |
| Cambiar el modelo de un agente | `AgentPlatform/agents/{capability}/{name}/manifest.yaml` (campo `spec.models[].bedrock.model_id`) |
| Cambiar un prompt | `AgentPlatform/agents/{capability}/{name}/prompts/system_prompt.yaml` |
| Permitir un nuevo modelo en la org | `Componentes-AgentCore/config_files/allowed_models.yml` |
| Crear un componente CI nuevo | `Componentes-AgentCore/templates/<nuevo>/template.yml` + `src/<nuevo>/<action>.py` |
| Crear una composition Terraform nueva | `Infra-AgentCore/compositions/<nueva>/` (copiar la más cercana) |
| Agregar una shard PRD nueva | Crear proyecto `iac/AgentCore/agentcore-prd-shard-X` (ver `MULTI_ACCOUNT.md`) |
| Agregar Cedar policies a un agente | `AgentPlatform/agents/.../policies/*.cedar` + `manifest.spec.gateway_policies[]` |
| Dar un permiso AWS específico a un agente | `manifest.spec.runtime_iam.managed_policy_arns` (path recomendado) o `inline_policies[]` |
| Cambiar el threshold de severity del scan | `Compose-AgentCore/pipeline_deploy_agents.yml` (input `severity_threshold`) |
| Cambiar el cron de drift detection | GitLab UI del proyecto deployable → Schedules |
