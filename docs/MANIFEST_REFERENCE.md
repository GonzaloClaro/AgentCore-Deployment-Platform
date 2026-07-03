# Manifest Reference — Piezas Lego de AgentCore

> **Objetivo:** documentar TODAS las piezas Lego (módulos Terraform + componentes CI) que la plataforma ofrece, separando claramente **qué decide el dev en el manifest** vs **qué impone la plataforma desde `env-defaults.yaml` o `foundation/`**.

## Cómo leer este documento

- **Configurable (manifest)**: el dev del workload lo declara en `manifest.yaml`.
- **No configurable (plataforma)**: viene de `iac/AgentCore/agentcore-{env}/env-defaults.yaml` o se hereda de `foundation/`. El dev no lo toca.
- **Auto-generado (pipeline)**: lo produce un componente CI durante el build (ECR URI, S3 zip URI, prompt ARNs, etc.).

---

## 1. Inventario completo de piezas Lego

### 1.1 Módulos Terraform (`Infra-AgentCore/modules/`)

| # | Módulo | Para qué sirve | Cómo se selecciona |
|---|---|---|---|
| 1 | `runtime` | Agent Runtime + alias `live` (versión inmutable) | **Siempre activo** (core) |
| 2 | `memory` | Memory + strategy (summarization / semantic / user-preference) | Flag `features.enable_memory` (default `true`); apagable con `runtime.memory_strategy: none` |
| 3 | `observability` | CloudWatch log group, X-Ray sampling, dashboard | Flag `features.enable_observability` (default `true`) |
| 4 | `knowledge-base` | Bedrock KB + S3 Vectors index | Flag `features.enable_kb` + presencia de `knowledge_base.sources` |
| 5 | `gateway-target` | Target en gateway (default o custom) | Lista `gateway_targets[]` (vacía = no se crean) |
| 6 | `identity-oauth-provider` | OAuth2 credential provider (3LO/2LO) | Bloque `oauth_provider` presente |
| 7 | `gateway` | Gateway AgentCore | `foundation/default-gateways` (3 default) o composition `gateway-deploy` (custom) |
| 8 | `workload-identity` | Workload Identity explícito | Avanzado, no expuesto por defecto |
| 9 | `lambda-tool` | Lambda ARM64 + role para tools como Lambda | Composition `tool-lambda` |
| 10 | `gateway-policy` | Policy Engine Cedar attached a un gateway (CLI oficial `agentcore`) | Flag `features.enable_policies` + `gateway_policies[]` con `cedar_files` |
| 11 | `runtime-role` | IAM role custom per-workload con managed/inline policies | Bloque `spec.runtime_iam` o flag `features.enable_custom_role` (en composiciones de agente) |

> **Prompts**: ya no hay módulo TF para prompts. Se publican vía SDK con el componente CI `publish_prompt` (Bedrock Prompt Management versiona nativo).

### 1.2 Componentes CI (`Componentes-AgentCore/templates/`)

| # | Componente | Para qué sirve | Cuándo corre |
|---|---|---|---|
| 1 | `validate_manifest` | Valida `manifest.yaml` contra JSON-schema | Stage `validate`, siempre |
| 2 | `package_artifact` | Zip del workload + upload S3 (auditable) | Stage `package`, siempre (soft-skip si `features.enable_artifact_audit: false` — el job corre pero no zipea/sube) |
| 3 | `build_image` | Docker buildx ARM64 + push ECR | Stage `build`, siempre |
| 4 | `scan_image` | Trivy/Inspector con gate por severity | Stage `scan`, siempre |
| 5 | `upload_secret` | CI var (masked) → Secrets Manager | Stage `secrets`, solo si hay secretos definidos |
| 6 | `publish_prompt` | YAMLs de prompts → Bedrock Prompt Mgmt (SDK, versionado nativo) | Stage `publish-prompts`, si hay `prompts[]` y `enable_prompts_terraform=false` |
| 7 | `render_tfvars` | manifest + env-defaults → `terraform.auto.tfvars.json` | Stage `render`, siempre |
| 8 | `trigger_iac` | Multi-project trigger al deployable `agentcore-{env}` | Stage `deploy` upstream |
| 9 | `smoke_test` | Invoca `/ping` del runtime | Stage `smoke`, post-apply |
| 10 | `publish_leanix` | Manifests → fact sheets LeanIX | Solo branch `main`, post-deploy |
| 11 | `deploy_agent` / `deploy_mcp` / `deploy_tool` | Macros (atajos) | Opcional, no se usan en flujo prod |
| 12 | `apply_policy` | Lee `.cedar` files del workload → `cedar_policies.json` (consumido por `render_tfvars`) | Stage `render`, si `gateway_policies[]` está presente |
| 13 | `validate_structure` | Validación cruzada: composition existe, requires presentes, archivos referenciados, naming | Stage `validate`, siempre |
| 14 | `pipeline_telemetry` | Genera/propaga TRACE_ID y emite eventos estructurados a CloudWatch Logs | Stage `.pre` (start) y `.post` (end) — cross-pipeline |
| 15 | `drift_check` | Analiza `terraform plan -json` y categoriza severidad de drift; alerta a SNS | Pipeline `drift_detection` scheduled |

---

## 2. Mapping piezas Lego ↔ campos del manifest

### 2.1 Metadata (siempre, todas las composiciones)

| Campo manifest | Configurable | Validación | Para qué |
|---|---|---|---|
| `metadata.name` | ✅ Dev | `^[a-z][a-z0-9-]{2,40}$` | Nombre del workload (kebab-case) |
| `metadata.capability` | ✅ Dev | `^[a-z][a-z0-9-]{2,40}$` | Capability (lista cerrada — pendiente workshop) |
| `metadata.owner` | ✅ Dev | string | Equipo dueño (visible en LeanIX) |
| `metadata.description` | ✅ Dev | string | Descripción humana |
| `metadata.tags` | ✅ Dev | list[string] | Tags AWS arbitrarios |
| `metadata.kind` | ✅ Dev | `agents` \| `mcp` \| `tools` | Tipo (default: derivado de composition) |

### 2.2 Composition selector

| Campo | Configurable | Valores | Para qué |
|---|---|---|---|
| `spec.composition` | ✅ Dev | `agent-chatbot` \| `agent-with-kb` \| `agent-with-tools` \| `mcp-server` \| `agent-full` | Qué directorio de `compositions/` ejecutar |

> 💡 Para combinaciones raras: usa `agent-full` y enciende solo los flags que quieras en `spec.features`.

### 2.3 Runtime (`module "runtime"`)

| Campo manifest | Configurable | Default | Mapea a (TF) | Origen |
|---|---|---|---|---|
| `spec.runtime.entrypoint` | ✅ Dev | — | usado por `Dockerfile` | manifest |
| `spec.runtime.env` | ✅ Dev | `{}` | `module.runtime.env_vars` | manifest |
| `spec.runtime.memory_strategy` | ✅ Dev | `summarization` | `module.memory.strategies[].type` | manifest |
| `spec.runtime.target_version` | ✅ Dev (rollback) | `null` (versión nueva) | `aws_bedrockagentcore_agent_runtime_alias.routing` | manifest |
| `spec.runtime.server_protocol` | ✅ Dev | `HTTP` | `module.runtime.server_protocol` (`protocol_configuration.server_protocol`) | manifest |
| `image_uri` | ⚙️ Auto | `ecr/agentcore-{kind}-{capability}-{name}:{sha}` | `module.runtime.image_uri` | pipeline (`build_image`) |
| `role_arn` | 🔒 Plataforma | — | `module.runtime.role_arn` | `env-defaults.default_role_arn` |
| `network_mode` | 🔒 Plataforma | `PUBLIC` | `module.runtime.network_mode` | hardcoded en módulo (cambiar requiere PR a Infra-AgentCore) |
| `vpc_id`, `subnet_ids` | 🔒 Plataforma | — | (futuro: si pasamos a `network_mode=VPC`) | `env-defaults.yaml` |
| `pipeline_id` | ⚙️ Auto | `$CI_PIPELINE_ID` | description de la version | pipeline |

### 2.4 Memory (`module "memory"`)

| Campo manifest | Configurable | Default | Mapea a |
|---|---|---|---|
| `spec.runtime.memory_strategy` | ✅ Dev | `summarization` | `strategies[0].type` |
| (event_expiry_seconds) | 🔒 Plataforma | 30 días | módulo (no expuesto por ahora) |

> Para deshabilitar memory: `memory_strategy: none`.

### 2.4.bis Patrón A2A / agents-as-tools

Un agente puede invocar a otro runtime AgentCore como "persona"/sub-agente vía protocolo A2A. No hace falta una composition especial: cualquiera de las 5 compositions con `module "runtime"` (`agent-base`, `agent-chatbot`, `agent-with-kb`, `agent-with-tools`, `mcp-server`) acepta `spec.runtime.server_protocol: A2A`.

```yaml
spec:
  composition: agent-chatbot
  runtime:
    entrypoint: agent.py
    server_protocol: A2A
    env:
      AGENTE_PERSONA_ARN: "arn:aws:bedrock-agentcore:us-east-1:111122223333:runtime/otro-agente-dev-xxxxx"
      AGENTE_PERSONA_PROTOCOL: "A2A"
```

**Limitación actual (deliberada):** el ARN del agente-persona se declara a mano en `runtime.env` — no hay descubrimiento automático (ni SSM Parameter Store, ni `terraform_remote_state`). El dev debe copiar el ARN del runtime ya desplegado. Ver `docs/01_IMPROVEMENTS_AND_FUTURE_WORK.md` §3.4 para el ítem de auto-discovery, evaluado y pospuesto.

### 2.5 Knowledge Base (`module "knowledge-base"`)

| Campo manifest | Configurable | Default | Mapea a |
|---|---|---|---|
| `spec.knowledge_base.embedding` | ✅ Dev | `amazon.titan-embed-text-v2:0` | `embedding_model_arn` |
| `spec.knowledge_base.sources_file` | ✅ Dev | — | path a YAML con `sources[]` |
| `spec.features.enable_kb` | ✅ Dev | `false` | `count` del módulo |
| `embedding_dimension` | 🔒 Plataforma | `1024` (titan-v2) | módulo |
| `role_arn` | 🔒 Plataforma | — | `env-defaults.default_role_arn` |

**Estructura de `sources_file` (ej: `kb/data_sources.yaml`):**
```yaml
sources:
  - name: docs-public
    bucket_arn: "arn:aws:s3:::my-org-kb-public"   # configurable por dev
    inclusion_prefixes: ["docs/"]
```

### 2.6 Gateway Targets (`module "gateway-target"`)

| Campo manifest | Configurable | Default | Mapea a |
|---|---|---|---|
| `spec.gateway_targets[].gateway` | ✅ Dev | — | uno de `oauth-3lo` \| `oauth-2lo` \| `sigv4-m2m` |
| `spec.gateway_targets[].tools_schema` | ✅ Dev | — | path local; se sube a S3 y la URI va a `target_configuration` |
| `spec.features.enable_tools` | ✅ Dev | `false` | activa el módulo en `agent-full` |
| `gateway_id` (resuelto desde nombre) | 🔒 Plataforma | — | `env-defaults.default_gateway_ids.<nombre>` |
| `use_native_resource` | 🔒 Plataforma | `false` (workaround #46128) | módulo |

### 2.7 OAuth Identity Provider (`module "identity-oauth-provider"`)

| Campo manifest | Configurable | Default | Mapea a |
|---|---|---|---|
| `spec.oauth_provider.client_id` | ✅ Dev | — | `client_id` |
| `spec.oauth_provider.client_secret_var` | ✅ Dev | `OAUTH_CLIENT_SECRET` | nombre de la CI var (component `upload_secret` la sube a Secrets Manager) |
| `spec.oauth_provider.issuer` | ✅ Dev | — | `issuer` |
| `spec.oauth_provider.authorization_endpoint` | ✅ Dev | — | `authorization_endpoint` |
| `spec.oauth_provider.token_endpoint` | ✅ Dev | — | `token_endpoint` |
| `client_secret_arn` | ⚙️ Auto | — | output del componente `upload_secret` |

### 2.8 Observability (`module "observability"`)

| Campo manifest | Configurable | Default | Mapea a |
|---|---|---|---|
| `spec.observability.enabled` | ✅ Dev | `true` | (informacional, redundante con flag) |
| `spec.observability.dashboard` | ✅ Dev | `false` | `enable_dashboard` |
| `spec.features.enable_observability` | ✅ Dev | `true` | `count` del módulo |
| `log_retention_days` | 🔒 Plataforma | `30` | módulo |
| `enable_xray` | 🔒 Plataforma | `true` | módulo |
| `kms_key_arn` | 🔒 Plataforma | — | `env-defaults.kms_key_arn` |

### 2.9 Prompts — ver §3

### 2.10 Features (flags booleanos de `agent-full`)

| Flag | Default | Activa |
|---|---|---|
| `features.enable_observability` | `true` | `observability.tf` |
| `features.enable_kb` | `false` | `knowledge_base.tf` (si hay `knowledge_base.sources`) |
| `features.enable_tools` | `false` | `gateway_targets.tf` (si hay `gateway_targets[]`) |
| `features.enable_prompts_terraform` | `false` | `prompts.tf` — ver §3 |

---

## 3. Models — Bedrock y Azure AI con whitelist gobernada

Los modelos LLM que un agente usa se declaran como **artefactos auditables** en el manifest, simétrico con los prompts. Cambiar de modelo = MR + review = audit trail.

### Por qué declarativo en lugar de hardcoded

- **Auditabilidad**: cada cambio queda en git. Compliance puede preguntar "¿qué modelo está activo en X agente en PRD?" — la respuesta es el manifest en `main`.
- **Promoción gradual**: el equipo puede usar Claude Opus en QA, comparar con Sonnet, promover el ganador a PRD via MR pequeño.
- **Multi-provider**: misma estructura para Bedrock o Azure. El agente detecta el provider en runtime.
- **Governance via whitelist**: `config_files/allowed_models.yml` lista modelos permitidos por la org, con scope por ambiente. `validate_structure` rechaza model_ids no aprobados.

### Estructura en el manifest

```yaml
spec:
  models:
    - alias: PRIMARY_MODEL                    # → env vars con prefijo PRIMARY_MODEL_*
      provider: bedrock
      bedrock:
        model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
        region: us-east-1                     # opcional
        # inference_profile_arn: arn:aws:bedrock:...:inference-profile/us.anthropic...

    - alias: AZURE_MODEL                      # multi-provider
      provider: azure
      azure:
        endpoint: "https://my-org.openai.azure.com/"
        deployment: "gpt-4o-prod"
        model_id: gpt-4o                      # validado contra whitelist
        api_version: "2024-08-01-preview"
        api_key_secret_var: AZURE_OPENAI_API_KEY    # CI var masked → Secrets Manager
```

### Env vars producidas en el runtime

Cada alias produce un set de env vars con su prefijo:

| Bedrock | Azure |
|---|---|
| `PRIMARY_MODEL_ID` | `AZURE_MODEL_ID` |
| `PRIMARY_MODEL_PROVIDER=bedrock` | `AZURE_MODEL_PROVIDER=azure` |
| `PRIMARY_MODEL_REGION` | `AZURE_MODEL_REGION` |
| `PRIMARY_MODEL_INFERENCE_PROFILE_ARN` (si aplica) | `AZURE_MODEL_ENDPOINT` |
| | `AZURE_MODEL_DEPLOYMENT` |
| | `AZURE_MODEL_API_VERSION` |
| | `AZURE_MODEL_API_KEY_SECRET_ARN` |

### Pattern de uso en código del agente

Helper estándar incluido en `_template/src/agent.py`:

```python
cfg = model_config("PRIMARY_MODEL")
if cfg["provider"] == "bedrock":
    bedrock = boto3.client("bedrock-runtime", region_name=cfg["region"])
    response = bedrock.converse(modelId=cfg["id"], messages=[...])
elif cfg["provider"] == "azure":
    api_key = get_azure_api_key(cfg["api_key_secret_arn"])   # cached
    client = AzureOpenAI(azure_endpoint=cfg["endpoint"], api_key=api_key, ...)
```

> **Nunca** `model_id = "anthropic.claude-..."` hardcoded. El alias del manifest es el contrato.

### Whitelist gobernada (`config_files/allowed_models.yml`)

Lista cerrada con scope por ambiente:

```yaml
bedrock:
  - id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
    environments: [dev, qa, prd]
  - id: "anthropic.claude-3-opus-20240229-v1:0"
    environments: [dev, qa]      # NO en prd (FinOps approval requerido)
```

**Agregar modelo nuevo:** PR + review (Arquitectura + InfoSec + FinOps).

### Flujo de cambio de modelo

1. Equipo prompt engineering quiere Opus en QA. MR al manifest.
2. `validate_structure` confirma Opus permitido en QA.
3. Deploy en QA, telemetría reporta latencia/costo.
4. Si Opus gana, MR para PRD → `validate_structure` falla (Opus solo `[dev, qa]`).
5. Primero PR a `allowed_models.yml` para promover Opus a `[dev, qa, prd]` con FinOps approval.
6. Una vez merged, MR de PRD pasa.

Cada paso queda auditado.

### Azure API key vía Secrets Manager

- API keys nunca como env var long-lived — `upload_secret` las sube a Secrets Manager con KMS.
- Convención naming: `agentcore/{env}/azure/{alias_lower}` (auto-resolved en `render_tfvars`).
- El módulo `runtime-role` agrega `secretsmanager:GetSecretValue` limitado a esos ARNs (least privilege).
- Si hay model Azure declarado, **se fuerza un role custom** aunque no haya `runtime_iam` — el default compartido no debe tener permisos a secretos de tenants específicos.

---

## 3.alt. Prompts: SIEMPRE vía SDK (`publish_prompt`)

Bedrock Prompt Management versiona nativamente — duplicarlo en Terraform genera ruido innecesario. **Decisión arquitectónica firme:** no hay módulo TF para prompts. Todos van vía componente CI `publish_prompt`.

### Estructura en el manifest

```yaml
spec:
  prompts:
    - file: ./prompts/system_prompt.yaml
      alias: SYSTEM_PROMPT_ARN     # env var inyectada al runtime con el ARN versionado
```

### Flujo

1. Dev edita `./prompts/system_prompt.yaml`.
2. Push.
3. `publish_prompt` → SDK → Bedrock crea versión inmutable.
4. ARN versionado se escribe en `prompt_arns.json`.
5. `render_tfvars` inyecta `{ alias: ARN }` como env var del runtime.

> Si en algún momento alguien necesita lifecycle acoplado runtime↔prompt (raro), se discute caso por caso. No hay escape hatch built-in.

---

## 3.ops. Observabilidad y robustez operacional

Para una organización con cientos de agentes, el pipeline tiene 4 capas de protección:

### Capa 1: Trace ID cross-pipeline (`pipeline_telemetry`)

Cada pipeline genera un `TRACE_ID` único en stage `.pre` y lo propaga via `dotenv` artifact a todos los stages siguientes — incluido el downstream pipeline (vía `trigger_iac` que pasa `TRACE_ID` como CI variable). Eventos estructurados se emiten a CloudWatch Logs en `/agentcore/pipeline-telemetry/<TRACE_ID>`.

**Para debug de fallas:** un compliance officer o SRE solo busca el `TRACE_ID` en CloudWatch y obtiene el flujo end-to-end (workload pipeline + downstream Terraform pipeline) en una sola query.

### Capa 2: Validación estructural (`validate_structure`)

Corre en stage `validate` (el primero). Detecta en 30 segundos:
- Composition declarada existe en `composition_map.yml`.
- Requires de la composition presentes en el manifest (ej: `agent-with-kb` → `knowledge_base`).
- Archivos `.cedar`, `.json` (IAM), `prompts/*.yaml` referenciados existen.
- `tool.kind=lambda` tiene `handler` declarado.
- Naming kebab-case correcto.

Sin esta capa, errores se descubren en stage `terraform-init` (8+ minutos después). Con ella: ~30 segundos.

### Capa 3: Tests automáticos del pipeline

| Tipo | Cobertura | Ejecución |
|---|---|---|
| Python unit (`pytest`) | `validate_structure`, `render_tfvars`, `apply_policy` (19+ tests) | En MR de `Componentes-AgentCore` |
| Integration (`pytest`) | Pipeline simulado: validate → apply_policy → render_tfvars | En MR de `Componentes-AgentCore` |
| Terraform validate | Sintaxis de cada módulo y composición | En MR de `Infra-AgentCore` |
| Terraform test (`*.tftest.hcl`) | Lógica módulos `runtime`, `runtime-role`, `gateway-policy` + composition `agent-chatbot` | En MR de `Infra-AgentCore` |
| Drift detection scheduled | `terraform plan -detailed-exitcode` nightly por shard, alertas SNS | Cron `0 3 * * *` |

### Capa 4: Lifecycle protection PRD (`RUNBOOK_DESTROY_PRD.md`)

Defensa en profundidad:
1. **IAM Deny** sobre el role del deployer PRD para `bedrock-agentcore:Delete*`, KMS scheduled deletion.
2. **Role separado** `agentcore-prd-emergency-destroyer` con MFA + lista cerrada de principals (no asumido por pipeline).
3. **Manual gate adicional** `prd-destroy-acknowledge` en `pipeline_infra.yml` cuando el plan incluye destroys.

---

## 3.aux. Multi-account sharding (`metadata.target_shard`)

Para banca con cientos de agentes, una sola cuenta PRD no escala (quotas de AgentCore: runtimes, memories, gateways, KBs por cuenta). Solución: **N cuentas PRD shardeadas**, cada una con su propio deployable bajo `iac/AgentCore/agentcore-prd-shard-X`.

### En el manifest

```yaml
metadata:
  name: chatbot-tier1
  capability: customer-support
  target_shard: prd-shard-a       # explícito, decisión inmovible
```

`render_tfvars` lee `target_shard` y `trigger_iac` apunta al deployable correspondiente. **No hay auto-balancing**: cambiar de shard requiere migración (destroy en A + create en B).

Ver doc dedicada: **[MULTI_ACCOUNT.md](./MULTI_ACCOUNT.md)** (cómo agregar cuenta nueva, cuándo dispara sharding, anti-patrones).

---

## 3.bis. AgentCore Policy (Cedar) — autorización fine-grained en gateway

> **GA marzo 2026.** Provider AWS Terraform aún NO expone `aws_bedrockagentcore_policy_engine`. Modelo con `null_resource` + CLI oficial `agentcore` (no `aws bedrock-agentcore-control`).

`AgentCore Policy` es **distinto a IAM**. Mientras IAM controla qué APIs de AWS puede llamar el role del runtime, **Cedar policies controlan qué tools (acciones del gateway) puede invocar cada principal autenticado**, evaluando incluso el contenido del request.

### Detalles oficiales importantes

- **Action format**: `AgentCore::Action::"<TargetName>___<tool_name>"` — TRIPLE underscore.
- **Resource**: `AgentCore::Gateway::"<arn-completo>"` — Cedar **NO admite wildcards**, debe ser ARN exacto. Esto fuerza un deploy en 2 fases: gateway primero, ARN se obtiene con `agentcore status`, luego se actualiza el `.cedar`.
- **`attach_mode`**: `LOGONLY` (shadow, default seguro) o `ENFORCE` (bloquea). Empezar siempre en LOGONLY, observar en CloudWatch, promover cuando no haya falsos negativos.
- **Comandos CLI**: `agentcore add policy-engine`, `agentcore add policy --source <file.cedar>`, `agentcore remove policy-engine`, `agentcore deploy`, `agentcore status`.

### Principals y semántica

- `AgentCore::OAuthUser` — usuarios autenticados via 3LO/2LO (JWT con tags `scope`, `role`, etc.)
- `AgentCore::IamEntity` — workloads autenticados via SigV4 (con `principal.id` que es ARN IAM)
- **Default deny** + **forbid wins** + **layering** (todas las policies aplicables deben permitir)

### Estructura en el manifest

```yaml
spec:
  gateway_policies:
    - gateway: oauth-3lo                       # uno de los 3 default o gateway custom
      cedar_files:
        - ./policies/insurance.cedar
        - ./policies/audit.cedar
  features:
    enable_policies: true
```

### Flujo

1. Dev escribe `.cedar` files en `agents/X/Y/policies/*.cedar`.
2. Componente CI `apply_policy` los lee y produce `cedar_policies.json` con el contenido como strings.
3. `render_tfvars` agrega ese JSON a `terraform.auto.tfvars.json` bajo `gateway_policies[]`.
4. Composition (`agent-full` o `gateway-deploy`) usa `module "gateway_policies"` que invoca `gateway-policy/` con `local-exec` sobre `aws bedrock-agentcore-control create-policy-engine` + `put-policy`.

> **Nota provider TF:** el recurso nativo Terraform no existe aún. Workaround `null_resource` + `local-exec` (mismo patrón que `gateway-target` issue #46128). Cuando salga `aws_bedrockagentcore_policy_engine`, switchear con `use_native_resource = true`.

---

## 3.ter. IAM policies del runtime (`spec.runtime_iam`) — opt-in

Por defecto, el runtime usa el **`default_role_arn` compartido** del ambiente (output de `foundation/bootstrap`). Funciona para 90% de los casos, pero algunos workloads necesitan permisos AWS específicos (ej: leer un bucket dedicado, invocar una Lambda, escribir en DynamoDB).

Cuando el manifest declara `spec.runtime_iam`, se crea un **role custom per-workload** y el runtime lo usa en lugar del default. Disponible en todas las composiciones de agente: `agent-base`, `agent-chatbot`, `agent-with-kb`, `agent-with-tools`, `mcp-server`.

### Dos modos de declaración

#### (a) `managed_policy_arns` — RECOMENDADO

```yaml
spec:
  runtime_iam:
    managed_policy_arns:
      - "arn:aws:iam::111122223333:policy/agentcore-shared-read-kb"
      - "arn:aws:iam::111122223333:policy/agentcore-shared-invoke-tools"
```

El equipo de **accesos** crea las managed policies con su propio control y CAB, y comparte los ARNs. Los devs solo declaran "atáchame estas". La auditoría queda del lado de accesos. Sin gate adicional necesario en el pipeline.

#### (b) `inline_policies` — self-service con gate

```yaml
spec:
  runtime_iam:
    inline_policies:
      - name: read-data-bucket
        file: ./iam/read-data.json
```

El dev declara el JSON directamente en el repo del workload. Útil para iterar rápido en DEV. **Recomendación:** agregar manual approval gate al pipeline antes del apply en QA y PRD para que accesos pueda revisar.

### Permission boundary corporativo

```yaml
spec:
  runtime_iam:
    permissions_boundary_arn: "arn:aws:iam::111122223333:policy/CorporatePermissionsBoundary"
```

Si la organización tiene boundary corporativo, se aplica al role custom y limita el efecto neto de cualquier policy attached.

### Bedrock invoke por default

`attach_bedrock_invoke: true` (default) agrega inline policy con `bedrock:InvokeModel`, `bedrock:Converse`, `bedrock:GetPrompt`. Casi todos los runtimes lo necesitan; opt-out solo si no se usa Bedrock directo (caso raro).

### Flujo end-to-end

1. Dev declara en manifest `spec.runtime_iam.{managed_policy_arns,inline_policies}`.
2. Componente CI `render_tfvars`:
   - Lee `inline_policies[].file` → resuelve a `policy_document` (string JSON serializado).
   - Pasa `runtime_iam` completo al `terraform.auto.tfvars.json`.
3. Composition `agent-full` evalúa `local.has_runtime_iam`:
   - Si vacío → runtime usa `default_role_arn` (módulo `runtime-role` no se invoca).
   - Si declarado → módulo `runtime-role` crea role + attach + boundary; runtime usa ese ARN.
4. Output `runtime_role_arn` queda visible para auditoría.

> **Por qué role per-workload (no inline policies sobre el default):** modificar el default rompe a otros agentes que lo comparten. Aislar = blast radius acotado por workload.

---

## 3.quater. Tool kinds — embedded vs lambda vs open_api

Una tool puede vivir en 3 lugares según `spec.tool.kind`:

| Kind | Infra TF | Cuándo usarla |
|---|---|---|
| `embedded` | **Ninguna** — código Python horneado en la imagen del agente | Tools simples, lógica determinística, comparten estado del agente, no requieren permisos especiales |
| `lambda` | `lambda-tool/` + `gateway-target/` (composition `tool-lambda`) | Tools pesadas, escalan separado, reusables entre agentes, requieren IAM policy propia |
| `open_api` | Solo `gateway-target/` (HTTP API ya existente) | Integrar APIs corporativas legacy con OpenAPI schema |

**Embedded** se hornea en el `Dockerfile` del agente; el dev importa `from tools.<name> import handler`. **Lambda** se despliega como zip ARM64 + `aws_lambda_function`. **Open_api** sube el schema OpenAPI a S3 y registra como `target_configuration.mcp.open_api_schema`.

---

## 4. Resumen ejecutivo: matriz dev vs plataforma

> **Regla mental:** el dev decide **QUÉ** quiere desplegar (composition + features + lo específico del workload). La plataforma decide **DÓNDE y CÓMO** (cuenta AWS, VPC, KMS, IAM, gateways).

### Lo que el dev controla en el manifest

```yaml
metadata: { name, capability, owner, description, tags }
spec:
  composition: <una de 7: agent-base | agent-chatbot | agent-with-kb | agent-with-tools | mcp-server | tool-lambda | gateway-deploy>
  runtime: { entrypoint, env, memory_strategy, server_protocol }
  knowledge_base: { embedding, sources_file }    # opcional
  prompts: [{ file, alias }]                     # opcional
  gateway_targets: [{ gateway, tools_schema }]   # opcional
  gateway_policies: [{ gateway, attach_mode, cedar_files }]   # opcional (Cedar)
  runtime_iam: { managed_policy_arns, inline_policies, permissions_boundary_arn }  # opcional (IAM)
  oauth_provider: { client_id, client_secret_var, issuer, ... }   # opcional
  tool: { kind: embedded|lambda|open_api, ... }  # solo si kind: tools
  observability: { enabled, dashboard }
  features: { enable_X: bool }
```

### Lo que la plataforma impone (no editable por dev)

| Cosa | Dónde vive |
|---|---|
| Cuenta AWS, region | `env-defaults.account_id`, `env-defaults.aws_region` |
| VPC ID, subnet IDs | `env-defaults.vpc_id`, `env-defaults.subnet_ids` |
| KMS keys | `env-defaults.kms_key_arn` (output de `foundation/bootstrap`) |
| Default IAM role | `env-defaults.default_role_arn` (output de `foundation/bootstrap`) |
| 3 default gateway IDs | `env-defaults.default_gateway_ids.{oauth_3lo,oauth_2lo,sigv4_m2m}` (output de `foundation/default-gateways`) |
| ECR repo naming | patrón `agentcore-{kind}-{capability}-{name}` (módulo `build_image`) |
| S3 bucket naming | patrón `artifacts-{env}-agentcore-{kind}` (foundation) |
| Network mode runtime | `PUBLIC` (hardcoded en módulo `runtime`; cambiar requiere PR) |
| Severity threshold scan | `HIGH` (default del componente `scan_image`; configurable en Compose) |
| Log retention CW | `30 días` (módulo `observability`) |
| Memory event expiry | `30 días` (módulo `memory`) |
| Embedding dimension | `1024` (titan-v2; cambiar requiere update del módulo `knowledge-base`) |

### Lo que el pipeline auto-genera (no se escribe en el manifest)

| Cosa | Producido por |
|---|---|
| `image_uri` (ECR) | `build_image` → `image_meta.json` |
| `artifact_s3_uri` (zip auditable) | `package_artifact` → `artifact_meta.json` |
| `prompt_arns` versionados | `publish_prompt` → `prompt_arns.json` (camino SDK) |
| `client_secret_arn` (Secrets Manager) | `upload_secret` → `secret_meta.json` |
| `terraform.auto.tfvars.json` | `render_tfvars` (combina manifest + env-defaults + outputs intermedios) |
| `composition_name.txt` | `render_tfvars` (extrae de `manifest.spec.composition`) |
