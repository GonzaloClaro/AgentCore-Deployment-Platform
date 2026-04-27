# Plan — Plataforma de despliegue Bedrock AgentCore

> **Nota de entrega:** al aprobar este plan, se copia este documento como `PLAN.md` (o `docs/plan-agentcore.md`) dentro del proyecto `/Users/gonzalo/AgentPlatform-Deployment/` para que quede versionado junto al código.

## Context

La organización tiene 3 cuentas AWS (`dev-agenticplatform`, `qa-agenticplatform`, `prd-agenticplatform`) y necesita una plataforma interna que permita a comunidades subir agentes IA, MCP servers y tools a Bedrock AgentCore con gobierno fuerte y mínima fricción para devs.

**Problema:** sin estandarización, cada equipo inventaría su propio Terraform y CI/CD, fragmentando seguridad, IAM, secretos y catálogo.

**Resultado esperado:** un dev agrega su agente bajo `AgentPlatform/agents/{capability}/{name}/`, escribe un `manifest.yaml` opinado, hace push a `dev`, y el pipeline despliega automáticamente en cuenta DEV con runtime + memory + observability + gateway-targets + KB + prompts cableados. Promoción a QA y PRD por MR + manual approval. LeanIX se publica desde `main`.

## Cumplimiento del framework DevOps de la organización

Este plan respeta los lineamientos internos del framework (los críticos están marcados 🔴):

| Lineamiento | Cómo se cumple |
|---|---|
| 🔴 Un repo por **dominio**, subdominios adentro | El dominio `agentcore` vive en `Componentes-AgentCore`. Subdominios = `validate_manifest`, `package_artifact`, `build_image`, `deploy_agent`, `deploy_mcp`, etc. NO repos separados por subdominio. |
| 🔴 Pipelines productivos NO viven en componentes | Componentes solo tienen `templates/` y `src/`. Toda la orquestación productiva (rules, tags, defaults, stages, environment) vive en `Compose-AgentCore`. |
| 🔴 Componente = 100% agnóstico (sin `rules`, `tags`, `default:`) | Todos los `template.yml` reciben `job_name`, `stage`, `image_runner` por `inputs`. Cero hardcode. |
| 🔴 Inputs tipados con `spec.inputs` + separador `---` | Cada `template.yml` empieza con bloque `spec.inputs` y separa con `---`. |
| 🟡 Nombres dinámicos de jobs vía inputs | `"$[[ inputs.job_name ]]"` en lugar de nombres fijos. |
| 🟡 `description` y `default` en cada input | Documentado en cada `template.yml`. |
| 🟡 Preferir Python sobre Bash | Lógica en `src/<subdominio>/<action>.py`; bash inline solo `!reference`. |
| 🟡 Branching `main` + `feat/***` | Componentes y Compose usan este modelo. Workloads usan `dev/qa/main` por requisito de promoción. |
| 🟡 README obligatorio | Cada repo tiene `README.md` con descripción, estructura, tabla de inputs, ejemplo de uso. |
| 🟡 Secrets como CI/CD vars protegidas/enmascaradas | OAuth Client ID/Secret nunca en código ni tfvars. |
| 🟡 Versionado al consumir: `@main`, SHA, tag, branch, `~latest` | Compose puede pinear `@v1.x.y` o `@main`. |
| 🟢 Reutilizar con `!reference` y `extends` interno | Bloques compartidos en `templates/includes/base/`. |
| 🟢 Patrón `pull_python_scripts_dominio.yml` | Existe en `templates/includes/base/` para descargar scripts al runner del compose. |

**Regla mental que sigue el plan:**
- **Componente** = "cómo hacer algo" (agnóstico, reutilizable, sin contexto productivo)
- **Compose** = "cuándo, dónde y con qué hacerlo" (rules, tags, ambientes, defaults)
- **Workload** = "qué hacer" (código del agente/MCP, manifest, trigger al compose)

## Decisiones tomadas

| Decisión | Valor |
|---|---|
| Repos GitLab | 4 base + 3 deployables (ver §1) |
| Workloads | Repo único `AgentPlatform` con `/agents/{capability}/{name}` y `/mcp/{capability}/{name}` |
| Runtime artifact | Zip-a-S3 como artefacto auditable + imagen ECR ARM64 construida en pipeline (Runtime AgentCore exige ECR ARM64; zip directo NO es soportado) |
| Promoción workloads | Branches `dev` / `qa` / `main`, mismo pipeline, solo cambian `tfvars` y `assume-role` |
| Selección módulos TF | Composiciones predefinidas + flags booleanos (no jinja-render de HCL) |
| Estado Terraform | GitLab-managed state, 3 proyectos GitLab separados (`agentcore-dev`, `agentcore-qa`, `agentcore-prd`) |
| Versionado runtime | Immutable versions + alias `live` (rollback = mover alias) |
| Default Gateways | 3 por ambiente (OAuth 3LO, OAuth 2LO, SigV4 M2M), creados en `foundation/`, NO por workload |

## 1. Estructura de repositorios

**5 buckets GitLab de alto nivel = 8 repos + 1 existente:**

```
/Componentes/
  └── agentcore                   # Repo: componentes CI/CD del dominio agentcore (templates + src + config_files)

/Componentes/Compose/
  └── agentcore                   # Repo: orquestación productiva (rules, tags, stages, includes de componentes)

/ia-generativa/
  ├── AgentPlatform               # Repo: workloads (agents, mcp, tools, prompts, kb)
  └── AgentArtifacts              # Repo existente (Kiro IDE), fuera de scope

/iac/AgentCore/
  ├── infra-agentcore             # Repo: módulos + composiciones Terraform (sin state)
  ├── agentcore-dev               # Repo deployable: tfvars dev + state GitLab + .gitlab-ci.yml
  ├── agentcore-qa                # Idem QA
  └── agentcore-prd               # Idem PRD
```

**Decisiones clave de la estructura:**

- **Grupo + sub-grupo `/Componentes` y `/Componentes/Compose`** deja explícita la dirección de dependencia: Compose consume Componentes, nunca al revés.
- **El bucket `/iac/AgentCore` expande a 4 repos** porque GitLab-managed Terraform state es per-project. El código de módulos/composiciones NO se duplica: los 3 deployables referencian `infra-agentcore` con `git::...?ref=v1.x.y`.
- **Sin Terragrunt:** los 3 deployables son slim (solo `env-defaults.yaml` + `.gitlab-ci.yml`), reusan composiciones del repo central.
- **Promoción dev→qa→prd = bump del tag** en cada deployable.

> Nota de naming: en este plan uso los nombres `Componentes-AgentCore`, `Compose-AgentCore`, `Infra-AgentCore` como **alias legibles** de los repos `/Componentes/agentcore`, `/Componentes/Compose/agentcore`, `/iac/AgentCore/infra-agentcore` respectivamente. Cuando creemos los repos en GitLab, usaremos los paths reales.

## 2. Detalle por repo

### 2.1 `Componentes-AgentCore` (dominio = `agentcore`)

Estructura conforme al framework:
```
Componentes-AgentCore/
│
├── templates/
│   ├── includes/
│   │   └── base/
│   │       ├── base_dominio_components.yml      # funciones reutilizables del dominio
│   │       ├── pull_config_files_dominio.yml    # descarga config_files
│   │       └── pull_python_scripts_dominio.yml  # descarga src/ al runner
│   │
│   ├── validate_manifest/template.yml           # valida manifest.yaml contra schema
│   ├── package_artifact/template.yml            # zip + upload S3
│   ├── build_image/template.yml                 # docker buildx ARM64 + push ECR
│   ├── scan_image/template.yml                  # Trivy/Inspector
│   ├── upload_secret/template.yml               # CI var → Secrets Manager
│   ├── render_tfvars/template.yml               # manifest + env-defaults → tfvars.json
│   ├── trigger_iac/template.yml                 # multi-project trigger a agentcore-{env}
│   ├── publish_prompt/template.yml              # Bedrock Prompt Mgmt
│   ├── publish_leanix/template.yml              # publica a LeanIX
│   ├── smoke_test/template.yml                  # invoca /ping del runtime
│   ├── deploy_agent/template.yml                # macro: empaqueta varios pasos típicos de un agente
│   └── deploy_mcp/template.yml                  # macro: empaqueta varios pasos típicos de un MCP
│
├── src/
│   ├── validate_manifest/
│   │   ├── base.py
│   │   └── validate.py
│   ├── package_artifact/
│   │   ├── base.py
│   │   └── package.py
│   ├── build_image/
│   │   ├── base.py
│   │   └── build.py
│   ├── scan_image/scan.py
│   ├── upload_secret/upload.py
│   ├── render_tfvars/render.py
│   ├── trigger_iac/trigger.py
│   ├── publish_prompt/publish.py
│   ├── publish_leanix/publish.py
│   ├── smoke_test/smoke.py
│   └── utils/
│       ├── aws_client.py
│       ├── manifest_parser.py
│       └── gitlab_client.py
│
├── config_files/
│   ├── shared/
│   │   └── common.yml                           # naming, tags AWS estándar, region defaults
│   ├── validate_manifest/
│   │   └── manifest.schema.json
│   ├── build_image/
│   │   ├── agent-runtime.Dockerfile             # FROM python:3.12 (ARM64), 8080, /invocations + /ping
│   │   └── mcp-server.Dockerfile
│   └── render_tfvars/
│       └── composition_map.yml                  # composition → variables esperadas
│
└── README.md                                    # OBLIGATORIO
```

**Ejemplo `template.yml` correcto (sin `rules`/`tags`/`default:` global):**
```yaml
spec:
  inputs:
    job_name:
      description: "Nombre del job (único en el pipeline consumidor)"
    stage:
      description: "Stage donde correrá el job"
      default: "deploy"
    image_runner:
      description: "Imagen Docker para el job"
      default: ""
    agent_name:
      description: "Nombre del agente a desplegar"
    capability:
      description: "Capability del agente"
    environment:
      description: "Ambiente destino"
      default: "dev"
---
include:
  - local: templates/includes/base/base_dominio_components.yml
  - local: templates/includes/base/pull_python_scripts_dominio.yml

"$[[ inputs.job_name ]]":
  stage: $[[ inputs.stage ]]
  image: $[[ inputs.image_runner ]]
  variables:
    COMPONENT_PY: deploy_agent
    ACTION: deploy
    AGENT_NAME: $[[ inputs.agent_name ]]
    CAPABILITY: $[[ inputs.capability ]]
    ENVIRONMENT: $[[ inputs.environment ]]
  script:
    - !reference [.pull_python_scripts, script]
    - python python_scripts/$COMPONENT_PY/$ACTION.py
```

### 2.2 `Compose-AgentCore`

Aquí SÍ van defaults, tags, rules, stages, environment:
```
Compose-AgentCore/
├── pipeline_deploy_agents.yml                  # orquesta el flujo completo de un agente
├── pipeline_deploy_mcps.yml                    # orquesta el flujo de un MCP
├── pipeline_infra.yml                          # incluido por agentcore-{env}
├── pipeline_foundation.yml                     # bootstrap por cuenta + 3 default gateways
├── pipeline_catalog.yml                        # publica LeanIX desde main
├── rules/
│   ├── branch-to-env.yml                       # dev→dev / qa→qa / main→prd + role_arn
│   ├── paths.yml                               # changes en agents/** mcp/** tools/**
│   └── approvals.yml                           # required approvals qa/prd
├── variables/
│   ├── env-dev.yml
│   ├── env-qa.yml
│   └── env-prd.yml
└── README.md
```

**Ejemplo `pipeline_deploy_agents.yml` (esqueleto):**
```yaml
stages:
  - validate
  - package
  - build
  - scan
  - secrets
  - publish-prompts
  - render
  - deploy
  - smoke
  - catalog

default:
  tags: [devsecops-common]

variables:
  IMAGE_BASE: <runner-image-organizacional>
  S3_ARTIFACTS_BUCKET: artifacts-${ENVIRONMENT}-agentcore

include:
  - component: $CI_SERVER_FQDN/ia-generativa/Componentes-AgentCore/validate_manifest@main
    inputs: { job_name: validate-manifest, stage: validate, image_runner: $IMAGE_BASE }
  - component: $CI_SERVER_FQDN/ia-generativa/Componentes-AgentCore/package_artifact@main
    inputs: { job_name: package, stage: package, image_runner: $IMAGE_BASE }
  - component: $CI_SERVER_FQDN/ia-generativa/Componentes-AgentCore/build_image@main
    inputs: { job_name: build-image, stage: build, image_runner: $IMAGE_BASE }
  # ... etc

# rules específicas dev/qa/prd viven aquí, no en componente
deploy-agent-dev:
  rules:
    - if: '$CI_COMMIT_BRANCH == "dev"'
deploy-agent-qa:
  extends: deploy-agent-dev
  variables: { ENVIRONMENT: qa }
  rules:
    - if: '$CI_COMMIT_BRANCH == "qa"'
      when: manual
deploy-agent-prd:
  extends: deploy-agent-dev
  variables: { ENVIRONMENT: prd }
  rules:
    - if: '$CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/'
      when: manual
```

### 2.3 `Infra-AgentCore` (módulos + composiciones, sin state)
```
Infra-AgentCore/
├── modules/
│   ├── runtime/                                # name, image_uri, role_arn, env_vars, memory_id?
│   ├── memory/                                 # name, strategies[]
│   ├── gateway/                                # name, authorizer_type
│   ├── gateway-target/                         # gateway_id, target_type, schema, credential_provider_arn
│   ├── identity-oauth-provider/                # client_id_secret_arn, client_secret_arn, issuer
│   ├── observability/                          # runtime_arn → CW logs, X-Ray, dashboard
│   ├── knowledge-base/                         # name, s3_data_source_arn, embedding_model
│   ├── prompt/                                 # name, version → prompt_arn:version
│   └── workload-identity/                      # opcional, casos avanzados
├── foundation/
│   ├── bootstrap/                              # ECR pattern, KMS, S3 artifact buckets, IAM cross-account
│   ├── default-gateways/                       # 3 gateways por ambiente (3LO, 2LO, SigV4)
│   └── vpc-endpoints/                          # endpoints Bedrock, S3, ECR, Secrets Manager
├── compositions/
│   ├── agent-chatbot/                          # runtime + memory + observability
│   ├── agent-with-kb/                          # + knowledge-base + prompt
│   ├── agent-with-tools/                       # + gateway-target(s)
│   ├── mcp-server/                             # gateway-target + identity-provider
│   └── agent-full/                             # todo
└── README.md                                   # contrato de inputs por composición
```

**Composiciones con flags:** cada `compositions/*/main.tf` consume variables tipadas y usa `count = var.enable_X ? 1 : 0` para módulos opcionales.

**Issues conocidas del provider AWS Terraform:**
- `aws_bedrockagentcore_gateway_target` aún no expone `grant_type` para OAuth (issue hashicorp/terraform-provider-aws#46128). Workaround: `local-exec` con AWS CLI hasta resolución.
- `aws_bedrockagentcore_agent_runtime` deja ENIs huérfanas en destroy (issue #45099). Documentar runbook de cleanup.

### 2.4 `AgentPlatform` (workloads)
```
AgentPlatform/
├── agents/
│   └── {capability}/{name}/
│       ├── manifest.yaml                       # contrato opinado (ver §3)
│       ├── src/
│       │   ├── agent.py
│       │   ├── requirements.txt
│       │   └── Dockerfile                      # opcional, override del default
│       ├── prompts/system_prompt.yaml
│       └── kb/data_sources.yaml                # rutas S3 a indexar (no datos)
├── mcp/{capability}/{name}/                    # misma estructura, composition: mcp-server
├── tools/                                      # libs Python compartidas
├── .gitlab-ci.yml                              # include: ia-generativa/Compose-AgentCore/pipeline_deploy_agents.yml
└── README.md                                   # cómo agregar un nuevo agente
```

### 2.5 `iac/agentcore-{env}` (deployables, x3)
```
agentcore-{env}/
├── .gitlab-ci.yml                              # include: ia-generativa/Compose-AgentCore/pipeline_infra.yml
├── backend.tf                                  # backend "http" → GitLab managed state
├── providers.tf                                # provider aws + assume-role a cuenta {env}
├── versions.tf                                 # pin terraform >=1.6, provider aws ~> 5.x
├── env-defaults.yaml                           # VPC IDs, subnets, KMS keys, account_id, IAM defaults
└── README.md
```

`modules-source.tf` se genera en pipeline (job `render_tfvars`) apuntando a `git::ssh://gitlab/.../Infra-AgentCore.git//compositions/{X}?ref={tag}`.

## 3. Manifest opinado (contrato workload ↔ plataforma)

`AgentPlatform/agents/customer-support/chatbot-tier1/manifest.yaml`:
```yaml
apiVersion: v1
kind: Workload
metadata:
  name: chatbot-tier1
  capability: customer-support
  owner: team-cx                                # → LeanIX
  description: "Tier 1 customer support chatbot with FAQ KB"
  tags: [chatbot, customer-facing]
spec:
  composition: agent-with-kb                    # selecciona compositions/agent-with-kb
  runtime:
    entrypoint: agent.py
    env: { LOG_LEVEL: INFO }
    memory_strategy: summarization
  knowledge_base:
    embedding: amazon.titan-embed-text-v2:0
    sources_file: ./kb/data_sources.yaml
  prompts:
    - file: ./prompts/system_prompt.yaml
      alias: SYSTEM_PROMPT_ARN                  # → env var inyectada al runtime
  gateway_targets:
    - gateway: oauth-3lo                        # uno de los 3 default
      tools_schema: ./openapi.yaml
  observability: { enabled: true, dashboard: true }
  features: { enable_observability: true, enable_tools: false }
```

JSON-schema vive en `Componentes-AgentCore/config_files/validate_manifest/manifest.schema.json`.

## 4. Flujo end-to-end

```
DEV: push branch=dev en AgentPlatform/agents/customer-support/chatbot-tier1/**
   │
   ▼ AgentPlatform/.gitlab-ci.yml hace include de Compose-AgentCore/pipeline_deploy_agents.yml
   │
   ├─[validate]        validate_manifest          (schema check)
   ├─[package]         package_artifact           (zip → s3://artifacts-dev-agentcore-agents/{capability}/{name}/{sha}.zip)
   ├─[build]           build_image                (zip → docker buildx --platform linux/arm64 → push ECR dev)
   ├─[scan]            scan_image                 (Trivy/Inspector, gate)
   ├─[secrets]         upload_secret              (CI masked vars → Secrets Manager dev → ARN)
   ├─[publish-prompts] publish_prompt             (prompts/*.yaml → Bedrock Prompt Mgmt → ARNs versionados)
   ├─[render]          render_tfvars              (manifest + env-defaults → terraform.auto.tfvars.json + composition)
   ├─[deploy]          trigger_iac                (multi-project pipeline trigger → ia-generativa/iac/agentcore-dev)
   │                                              (artefactos: tfvars + composition_name + tag Infra-AgentCore)
   │
   ▼ iac/agentcore-dev pipeline (downstream, usa pipeline_infra.yml)
   │
   ├─[init]            terraform init             (backend GitLab state)
   ├─[plan]            terraform plan             (cd compositions/{X}, -var-file=tfvars, -var ecr_uri=...)
   ├─[approval]        manual gate (qa/prd solo)
   └─[apply]           terraform apply            (immutable: nueva versión runtime + alias 'live')
   │
   ▼
   ├─[smoke]           smoke_test                 (invoca /ping del runtime)
   └─[catalog]         publish_leanix             (solo branch=main, lee todos los manifests)
```

**Promoción QA/PRD:** mismo pipeline, branch=qa→ENV=qa→trigger a `agentcore-qa`; tag semver→ENV=prd→manual approval→`agentcore-prd`.

## 5. Componentes técnicos críticos

### 5.1 Empaquetado y construcción de imagen
- `package_artifact/package.py`: produce `{sha}.zip` con `src/ + requirements.txt + manifest.yaml`. Sube a `s3://artifacts-{env}-agentcore-{kind}/{capability}/{name}/{sha}.zip`. Mantiene puntero `latest.zip`. Buckets versionados con lifecycle.
- `build_image/build.py`: descarga zip, ejecuta `docker buildx build --platform linux/arm64 -f config_files/build_image/agent-runtime.Dockerfile -t {ecr}:{sha} --push`. Una repo ECR por workload: `agentcore-{kind}-{capability}-{name}`.

### 5.2 Render de tfvars (sin generar HCL)
`render_tfvars/render.py` consume:
- `manifest.yaml` del workload
- `env-defaults.yaml` del proyecto `agentcore-{env}`
- Outputs intermedios (ECR URI, prompt ARNs, secret ARNs)

Produce:
- `terraform.auto.tfvars.json` — variables tipadas
- `composition_name.txt` — qué `compositions/<name>/` ejecutar

`pipeline_infra.yml` hace `terraform -chdir=compositions/$(cat composition_name.txt) plan`. **No se genera HCL dinámico.**

### 5.3 Default Gateways (Foundation)
`Infra-AgentCore/foundation/default-gateways/main.tf` crea los 3 gateways por ambiente. `pipeline_foundation.yml` se dispara solo cuando cambian `foundation/**`. Workloads agregan `aws_bedrockagentcore_gateway_target` por nombre conocido (`oauth-3lo`, `oauth-2lo`, `sigv4-m2m`).

### 5.4 Secrets Identity (OAuth Client ID/Secret)
`upload_secret/upload.py` recibe valores como GitLab CI variables (masked + protected, scope=environment), los sube a Secrets Manager con KMS dedicado. Módulo `identity-oauth-provider` recibe el ARN y crea `aws_bedrockagentcore_oauth2_credential_provider`. **Nunca** secretos en código ni en tfvars.

### 5.5 Prompts y referencia desde el agente
`publish_prompt/publish.py` registra el prompt en Bedrock Prompt Management y devuelve `arn:aws:bedrock:...:prompt/ID:VERSION`. Este ARN se inyecta al Runtime como env var (alias declarado en manifest). El agente Python lo lee con SDK (`bedrock-runtime.get_prompt`).

### 5.6 Versionado runtime + rollback
Cada `terraform apply` produce nueva versión inmutable de `aws_bedrockagentcore_agent_runtime`. Un alias `live` (`aws_bedrockagentcore_agent_runtime_alias`) apunta a la versión deseada. Rollback = MR cambiando `var.runtime_target_version`. Cero downtime.

### 5.7 Catálogo LeanIX
`publish_leanix/publish.py` corre solo en branch `main` post-apply. Lee `metadata` de manifests y mapea a fact sheets de LeanIX. **Schema exacto de mapping** queda como TODO de workshop con arquitectura.

## 6. Archivos críticos a crear (ordenados por dependencia)

**Bootstrap inicial:**
- `Componentes-AgentCore/README.md` y `templates/includes/base/{base_dominio_components,pull_config_files_dominio,pull_python_scripts_dominio}.yml`
- `Componentes-AgentCore/config_files/validate_manifest/manifest.schema.json`
- `Componentes-AgentCore/config_files/build_image/agent-runtime.Dockerfile`
- `Componentes-AgentCore/templates/validate_manifest/template.yml` + `src/validate_manifest/validate.py`
- `Infra-AgentCore/foundation/bootstrap/main.tf` (ECR pattern, KMS, S3 artifact buckets, IAM cross-account)
- `Infra-AgentCore/foundation/default-gateways/main.tf`

**Módulos Terraform (uno a uno, validables):**
- `runtime/`, `memory/`, `observability/`, `gateway-target/`, `identity-oauth-provider/`, `knowledge-base/`, `prompt/`

**Composiciones (en orden de complejidad):**
- `agent-chatbot/` (la más simple, valida el patrón)
- `agent-with-kb/`, `mcp-server/`, `agent-with-tools/`, `agent-full/`

**Componentes CI/CD restantes:**
- `package_artifact`, `build_image`, `scan_image`, `upload_secret`, `render_tfvars`, `trigger_iac`, `publish_prompt`, `publish_leanix`, `smoke_test`, `deploy_agent`, `deploy_mcp` (cada uno con `templates/<sub>/template.yml` + `src/<sub>/<action>.py`)

**Compose pipelines:**
- `pipeline_deploy_agents.yml`, `pipeline_deploy_mcps.yml`, `pipeline_infra.yml`, `pipeline_foundation.yml`, `pipeline_catalog.yml`
- `rules/{branch-to-env,paths,approvals}.yml`, `variables/env-{dev,qa,prd}.yml`

**Deployables iac (x3):**
- `iac/agentcore-{dev,qa,prd}/.gitlab-ci.yml`, `backend.tf`, `providers.tf`, `env-defaults.yaml`, `README.md`

**AgentPlatform scaffold:**
- `.gitlab-ci.yml`, `README.md`, `agents/_template/manifest.yaml`

## 7. Verificación end-to-end

1. **Smoke en DEV:** crear `agents/sandbox/hello-world/` que solo responde "hello". Push a `dev`. Verificar:
   - Zip en `s3://artifacts-dev-agentcore-agents/sandbox/hello-world/{sha}.zip`.
   - Imagen en ECR `agentcore-agents-sandbox-hello-world:{sha}`.
   - Runtime ARN existe; `terraform plan` siguiente da 0 cambios.
   - `aws bedrock-agentcore invoke --agent-runtime-arn ... --payload '{"prompt":"hi"}'` responde.
2. **Promoción a QA:** MR `dev`→`qa`, pipeline corre idéntico, recursos aparecen en cuenta QA.
3. **Promoción a PRD:** tag semver, manual approval, recursos en PRD.
4. **Rollback:** MR cambia `runtime_target_version`, alias `live` se mueve, smoke pasa con código viejo.
5. **Composición distinta:** segundo agente con `composition: agent-with-kb` despliega además KB y prompt.
6. **MCP server:** workload `mcp/finance/invoices-mcp/` con `composition: mcp-server` agrega target al gateway `oauth-3lo`.
7. **Catálogo:** post-merge a `main`, fact sheets aparecen/actualizan en LeanIX.

## 8. Riesgos y TODOs

1. **Issue Terraform #46128** (gateway_target sin `grant_type`): aceptar workaround `local-exec` o esperar fix upstream.
2. **Issue Terraform #45099** (ENIs huérfanas en destroy de runtime): runbook de cleanup; considerar job `cleanup-orphans` programado.
3. **LeanIX schema:** workshop con arquitectura para mapping manifest → fact sheets antes de implementar `publish_leanix`.
4. **Cross-account KB:** default propuesto = co-localizada por ambiente (más simple). Re-evaluar si los datos viven en data-lake separado.
5. **Buildx ARM64 en runners:** confirmar disponibilidad de runners ARM organizacionales o usar emulación QEMU (más lenta).
6. **Rotación de secretos OAuth:** fuera de MVP, v2.
7. **Tools shared:** path en monorepo por ahora; migrar a CodeArtifact si crece.
8. **Naming convention de capabilities:** definir lista cerrada (alineada a LeanIX) antes de aceptar PRs.
9. **Imagen runner organizacional:** identificar la imagen base (`IMAGE_BASE`) que se usa en pipelines y referenciarla desde `variables/env-*.yml`.
10. **`pull_python_scripts_dominio.yml`:** depende de un GitLab token con permiso `read_api`. Definir dónde se obtiene.

## 9. Orden sugerido de construcción

1. **Foundation** (`Infra-AgentCore/foundation/bootstrap/`) — aplicar manualmente una vez por cuenta (ECR pattern, KMS, IAM cross-account, S3 artifact buckets).
2. **Includes base** del componente + templates `validate_manifest` y `package_artifact` — primer flujo mínimo.
3. **Módulo `runtime`** + composición `agent-chatbot` mínima — validar fin a fin con un hello-world.
4. **Componentes restantes core**: `build_image`, `render_tfvars`, `trigger_iac`.
5. **Pipeline `pipeline_deploy_agents.yml`** + scaffold `AgentPlatform`.
6. **Default gateways** (foundation) + módulos `gateway-target`, `identity-oauth-provider` + componente `upload_secret`.
7. **Módulos `memory`, `observability`** + composición `agent-with-kb` + módulos `knowledge-base`, `prompt` + componente `publish_prompt`.
8. **Composición `mcp-server`** + scaffold MCP en `AgentPlatform/mcp/`.
9. **Catalog** + LeanIX.
10. **Hardening:** scan-image gates, approvals, runbooks, alarmas Observability.
