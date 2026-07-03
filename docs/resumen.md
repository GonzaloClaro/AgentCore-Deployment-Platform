# Resumen — AgentPlatform Deployment

Documento educativo sobre cómo está organizado el sistema de despliegue de agentes y MCPs sobre AWS Bedrock AgentCore. Cubre los 5 repos involucrados, el rol de cada uno, y el flujo end-to-end desde un commit en un manifest hasta los recursos AWS creados.

## Tabla de contenidos

1. [Visión general — los 5 repos](#1-visión-general)
2. [AgentPlatform — los workloads](#2-agentplatform)
3. [Componentes-AgentCore — piezas reutilizables de CI/CD](#3-componentes-agentcore)
4. [Compose-AgentCore — el orquestador](#4-compose-agentcore)
5. [Infra-AgentCore — el código Terraform](#5-infra-agentcore)
   - [5.1 `foundation/`](#51-foundation)
   - [5.2 `modules/` — los 4 archivos](#52-modules)
   - [5.3 `compositions/` — cómo se ensamblan los modules](#53-compositions)
6. [iac/AgentCore/agentcore-{env} — los deployables](#6-deployables)
7. [Flujo end-to-end de despliegue](#7-flujo-end-to-end)

---

## 1. Visión general

El sistema está dividido en 5 repos GitLab, cada uno con un rol específico. Esta separación no es estética: cada repo tiene un **ciclo de vida** y un **owner** distintos, y mezclarlos rompería las garantías de seguridad o auditoría.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  AgentPlatform               (workloads — agentes/MCPs/tools)            │
│  └─ commit en manifest.yaml dispara pipeline                             │
│         │                                                                 │
│         ▼ include                                                         │
│  Compose-AgentCore           (orquestador — pipeline_*.yml)              │
│  └─ define stages, rules, environment, runners                           │
│         │                                                                 │
│         ▼ include: - component:                                           │
│  Componentes-AgentCore       (componentes reutilizables — Python + YAML) │
│  └─ valida manifest, builda imagen, scanea, renderiza tfvars             │
│         │                                                                 │
│         ▼ multi-project trigger                                           │
│  iac/AgentCore/agentcore-{dev|qa|prd}  (deployables — terraform state)   │
│  └─ clona Infra-AgentCore en el tag fijado, corre terraform apply      │
│         │                                                                 │
│         ▼ source = "../../modules/X"                                      │
│  Infra-AgentCore             (código Terraform — modules + compositions) │
│  └─ define los recursos AWS                                              │
└──────────────────────────────────────────────────────────────────────────┘
```

| Repo | Rol | Lenguaje principal | Quién lo modifica |
|------|-----|-------------------|-------------------|
| `AgentPlatform` | Manifests + código del agente | Python + YAML | Equipos de capabilities (devs de agentes) |
| `Compose-AgentCore` | Pipelines GitLab | YAML (cero Python) | Equipo de plataforma |
| `Componentes-AgentCore` | Lógica reutilizable de CI/CD | Python + YAML | Equipo de plataforma |
| `Infra-AgentCore` | Terraform (modules + compositions) | HCL | Equipo de plataforma + revisión arquitectura |
| `iac/AgentCore/agentcore-{env}` | State Terraform por ambiente | YAML + tfvars | Equipo de plataforma (1 vez por env) |

---

## 2. AgentPlatform

Repo donde viven los **workloads**: agentes, MCP servers y tools compartidos. Es lo que un dev de capability modifica día a día.

```
AgentPlatform/
├── .gitlab-ci.yml           # trigger al Compose, detecta cambios por path
├── agents/
│   └── {capability}/{name}/
│       ├── manifest.yaml    # ⭐ contrato declarativo del workload
│       ├── src/
│       │   ├── agent.py     # entrypoint del agente
│       │   ├── requirements.txt
│       │   └── Dockerfile   # opcional, override del default
│       ├── prompts/         # versionados en Bedrock Prompt Management
│       └── kb/              # data sources para Knowledge Base
├── mcp/                     # estructura idéntica, composition: mcp-server
└── tools/                   # libs Python compartidas
```

**Idea clave**: cada workload tiene un `manifest.yaml` que declara **qué arquetipo** es (`spec.composition`: `agent-chatbot`, `agent-with-tools`, `agent-with-kb`, `mcp-server`, `tool-lambda`, `gateway-deploy`) y qué **features** activa. Ese manifest se proyecta en variables Terraform al final del pipeline.

**Detección por path**: el `.gitlab-ci.yml` usa `rules: changes:` para disparar pipelines distintos según qué directorio se modificó (`agents/**`, `mcp/**`). Eso permite despliegues granulares — modificar un agente no redespliega los otros 50.

**Promoción**: branches `dev` → `qa` → `main` (tag `vX.Y.Z` para PRD), con manual approval entre QA y PRD.

---

## 3. Componentes-AgentCore

Repo de **componentes CI/CD reutilizables**. Cada componente expone un job genérico via `include: - component:`. La regla dura: **cero `rules`/`tags`/`default:` aquí** — esos viven en Compose. Aquí solo lógica.

```
Componentes-AgentCore/
├── templates/                   # consumibles vía include: - component:
│   └── <subdominio>/template.yml  # un componente publicable
├── src/                         # lógica Python ejecutada por los jobs
│   ├── <subdominio>/<action>.py
│   └── utils/                   # helpers compartidos (aws, manifest, gitlab)
└── config_files/                # YAMLs de configuración (no de pipeline)
    └── <subdominio>/
```

### Subdominios principales

| Subdominio | Acción | Responsabilidad |
|------------|--------|-----------------|
| `validate_manifest` | `validate.py` | Valida `manifest.yaml` contra JSON-schema. Falla si falta algo o tipos incorrectos. |
| `validate_structure` | — | Cross-validation: que el código matche lo declarado en manifest |
| `package_artifact` | `package.py` | Zipea `src/` del workload, sube a S3 con KMS, devuelve `artifact_s3_uri` |
| `build_image` | `build.py` | `docker buildx --platform linux/arm64` y push a ECR (tag = git SHA) |
| `scan_image` | `scan.py` | Trivy/Inspector — gate que falla si hay CVEs HIGH+ |
| `upload_secret` | `upload.py` | CI variable masked → AWS Secrets Manager (devuelve ARN) |
| `apply_policy` | — | Lee archivos `.cedar` del workload, los serializa a JSON consumible por terraform |
| `render_tfvars` | `render.py` | Combina `manifest + env-defaults` → `terraform.auto.tfvars.json` + `composition_name.txt` |
| `trigger_iac` | `trigger.py` | Multi-project trigger al deployable `agentcore-{env}` con TFVARS_JSON |
| `publish_prompt` | `publish.py` | Registra/versiona prompt en Bedrock Prompt Management vía SDK |
| `smoke_test` | `smoke.py` | Invoca `/ping` del runtime tras apply para validar que está vivo |
| `pipeline_telemetry` | — | Genera `TRACE_ID` + emite eventos start/end (para auditoría) |
| `drift_check` | — | Detecta diff entre state terraform y AWS real |

### Anatomía de un componente

Cada subdominio tiene 3 partes:

1. **`templates/<sub>/template.yml`** — la definición pública del componente. Declara `spec.inputs` (los parámetros que acepta) y un `job_name` parametrizado con `"$[[ inputs.job_name ]]"`. Esto es lo que `Compose-AgentCore` consume vía `include: - component:`.

2. **`src/<sub>/<action>.py`** — la lógica real. El `template.yml` invoca este script. Razón de ser Python: tipado, testing, manejo de errores estructurado, vs bash inline que es frágil.

3. **`config_files/<sub>/`** — datos de configuración (JSON-schemas, mapeos, defaults). Por ejemplo `config_files/validate_manifest/manifest.schema.json` define qué campos puede tener un manifest.

### Por qué separado de Compose

Componentes es una **librería** de jobs. Compose es el **director de orquesta** que decide cuándo y en qué orden invocarlos. Esto permite:
- **Reutilización**: el mismo `validate_manifest` lo usan los pipelines de agentes, MCPs y foundation.
- **Versionado independiente**: Componentes sigue semver; Compose pinea tag específico (`@v1.2.3`).
- **Testabilidad**: la lógica Python tiene unit tests sin necesitar GitLab.

---

## 4. Compose-AgentCore

Repo de **orquestación productiva**. **Solo YAML**, cero Python. Define los pipelines que consumen los componentes y agrega rules, tags, environment, etc.

```
Compose-AgentCore/
├── pipeline_deploy_agents.yml      # cuando cambian agents/**
├── pipeline_deploy_mcps.yml        # cuando cambian mcp/**
├── pipeline_infra.yml              # downstream — corre terraform apply
├── pipeline_foundation.yml         # bootstrap por cuenta
├── pipeline_catalog.yml            # publica metadata a LeanIX
├── pipeline_drift_detection.yml    # cron que detecta drift en prod
├── rules/
│   ├── branch-to-env.yml           # mapea branch → environment + role_arn
│   ├── paths.yml                   # rules de cambios por path
│   └── approvals.yml               # required approvals para qa/prd
└── variables/
    ├── env-dev.yml                 # IMAGE_BASE, S3_BUCKET, AWS_ROLE_ARN
    ├── env-qa.yml
    └── env-prd.yml
```

### `pipeline_deploy_agents.yml` — el flujo principal

Es el pipeline más representativo. Stages (en orden):

```
.pre              telemetry start (genera TRACE_ID)
validate          validate_manifest + validate_structure
package           package_artifact (zip → S3)
build             build_image (docker buildx ARM64 → ECR)
scan              scan_image (Trivy gate)
secrets           upload_secret (CI vars → Secrets Manager)
publish-prompts   publish_prompt (Bedrock Prompt Mgmt)
render            apply_policy + render_tfvars
deploy            trigger_iac (multi-project trigger al deployable)
smoke             smoke_test (/ping al runtime)
.post             telemetry end
```

Cada stage es un `include: - component:` de Componentes con sus `inputs:` específicos. **Compose no implementa nada** — solo conecta componentes en el orden correcto y aplica las `rules:` (qué stage corre en qué branch, qué requiere approval, etc.).

### `pipeline_infra.yml` — el downstream

Lo incluye cada deployable (`agentcore-dev`, `agentcore-qa`, `agentcore-prd`). Es el que efectivamente corre `terraform init/plan/apply` con los inputs que recibió del trigger.

### Por qué separado de Componentes

Compose centraliza decisiones que NO son lógica:
- **Promoción**: `dev` no requiere approval; `qa` y `prd` sí.
- **Tags de runner**: PRD usa runners aislados con scope=`environment`.
- **Variables de ambiente**: AWS account ID, role ARN, bucket pattern — distintos por env.
- **Rules de paths**: agentes vs MCPs vs tools disparan pipelines distintos.

Si esto estuviera en Componentes, cada cambio de política operativa (ej: requerir approval también en QA) requeriría tocar la librería. Separados, Compose se puede modificar sin tocar la lógica que ejecuta.

---

## 5. Infra-AgentCore

Repo del código Terraform. **Sin state propio** — los deployables tienen el state, este repo solo tiene el código que se versiona con tags semver.

```
Infra-AgentCore/
├── foundation/        # cosas que existen UNA vez por cuenta AWS
├── modules/           # piezas Lego, una por cada componente AgentCore
├── compositions/      # recetas que ensamblan modules para un arquetipo
├── scripts/tf-check.sh     # harness fmt + validate
├── .gitlab-ci.yml          # CI propio: solo fmt-check + validate (no apply)
└── .gitignore
```

### 5.1 `foundation/`

Foundation contiene recursos que existen **una sola vez por cuenta AWS** (no uno por workload). Si los pusieras dentro de cada composition, los crearías N veces y tendrías conflicto de nombres. Tres subdirectorios, **cada uno con su propio terraform state**:

#### `foundation/bootstrap/` — el esqueleto de la cuenta

Crea:
- **2 KMS keys**: una para artefactos (S3 buckets de zips), otra para Secrets Manager
- **3 S3 buckets** versionados y encriptados: `artifacts-{env}-agentcore-{agents|mcp|tools}`. Aquí van los artefactos auditables.
- **IAM role base** `agentcore-{env}-runtime-execution` (asumido por todos los runtimes que no declaren `runtime_iam` custom en el manifest)
- **En PRD solamente**: una `deployer_deny_destroy_prd` policy con `Deny` explícito a `bedrock-agentcore:Delete*` + un role separado `emergency_destroyer` con MFA + lifecycle protection. Defensa en profundidad: si el pipeline GitLab se compromete, no puede borrar cosas críticas; un humano necesita asumir el `emergency_destroyer` con MFA reciente.

Se ejecuta **una vez** cuando se da de alta la cuenta dev/qa/prd.

#### `foundation/default-gateways/` — los 3 gateways del ambiente

Crea los 3 gateways AgentCore que comparten todos los workloads:

| Gateway | Para qué |
|---------|----------|
| `oauth-3lo` | Human-machine OAuth 3LO (con JWT del IdP corporativo) |
| `oauth-2lo` | Machine-to-machine OAuth 2LO (client_credentials) |
| `sigv4-m2m` | Machine-to-machine con SigV4 (AWS_IAM authorizer) |

Los workloads (agentes, MCPs, Lambdas-tool) **no crean gateways**. Solo agregan `gateway-target` a alguno de estos 3, vía `var.default_gateway_ids` (que viene del `env-defaults.yaml` del deployable).

#### `foundation/vpc-endpoints/` — tráfico privado

VPC endpoints para `bedrock-runtime`, `bedrock-agent-runtime`, `ecr.api`, `ecr.dkr`, `secretsmanager`, `logs`, `sts`. Sin esto, los agentes salen a internet pública para hablar con AWS. Con esto, todo el tráfico se queda dentro de la VPC.

#### Por qué state separado

Cada foundation tiene su propio terraform state. Si fuera el mismo state que las compositions:
- Cualquier workload podría ver/modificar las KMS keys de la cuenta
- Un `terraform destroy` mal apuntado en un workload podría borrar infraestructura compartida

Estados separados = **blast radius limitado**. Foundation se aplica raramente y por humanos con permisos elevados; compositions se aplican cada deploy con permisos limitados.

### 5.2 `modules/`

Cada module Terraform es una **función pura**: tiene inputs (`variables.tf`), outputs (`outputs.tf`), un cuerpo (`main.tf`), y declara sus dependencias (`versions.tf`). La regla del repo: **un module = un componente AgentCore** (ej: runtime, memory, observability) — no un mega-module que hace todo.

```
modules/
├── runtime/              # AgentCore Agent Runtime
├── runtime-role/         # IAM role custom para el runtime (opcional)
├── memory/               # AgentCore Memory
├── observability/        # CloudWatch logs + dashboards + transaction search
├── knowledge-base/       # Bedrock Knowledge Base + S3 Vectors
├── lambda-tool/          # Lambda function que actúa como tool
├── gateway/              # AgentCore Gateway (uso reservado; default-gateways están en foundation)
├── gateway-target/       # Target dentro de un gateway
├── gateway-policy/       # Cedar policies attachadas a un gateway
├── identity-oauth-provider/   # OAuth2 credential provider
└── workload-identity/    # Workload identity para inter-service auth
```

#### Los 4 archivos canónicos

##### `variables.tf` — los inputs (qué necesita saber el module)

```hcl
variable "name" {
  type        = string
  description = "Nombre del runtime (kebab-case)"
}

variable "memory_id" {
  type        = string
  description = "ID de Memory asociado (opcional)"
  default     = null   # ← default presente → input opcional
}
```

Declara **qué información** le tiene que pasar el caller. Cada `variable`:
- `type`: el shape (`string`, `list(string)`, `object({...})`, etc.). Si el caller pasa otro shape, terraform falla en plan.
- `default` (opcional): si lo declarás, la variable es opcional. Sin default, es **required**.
- `description`: documentación que aparece en `terraform plan` y `terraform-docs`.

Es la **firma pública** del module hacia afuera. Pensarlo como contrato.

##### `main.tf` — el cuerpo (qué hace el module)

```hcl
locals {
  model_env_vars = merge([for m in var.models : {...}]...)
}

resource "aws_bedrockagentcore_agent_runtime" "this" {
  agent_runtime_name = var.name
  role_arn           = var.role_arn
  ...
}
```

Vive **la lógica**:
- `locals { ... }`: variables computadas locales (no expuestas afuera). Para pre-procesar inputs.
- `data "..." { ... }`: queries a AWS (read-only). Ej: `data "aws_caller_identity" "current" {}`.
- `resource "..." { ... }`: los recursos que el module **crea y gestiona**. Cada `resource` queda en el state.

Convención: cuando un module crea **un único recurso del tipo principal**, lo llamás `"this"`. Si crea varios del mismo tipo, los nombrás explícitamente.

##### `outputs.tf` — qué expone el module hacia afuera

```hcl
output "agent_runtime_arn" {
  value = aws_bedrockagentcore_agent_runtime.this.agent_runtime_arn
}

output "models_summary" {
  value = [for m in var.models : { alias = m.alias, ... }]
  description = "Resumen de modelos inyectados al runtime (audit trail)."
}
```

El **return value** del module. Quien llame al module accede a estos valores como `module.runtime.agent_runtime_arn`.

Patrón importante: los outputs son los puntos de **conexión** entre modules. Por ejemplo, una composition hace `memory_id = module.memory.memory_id` — toma el output de un module y lo pasa como input a otro. Terraform infiere automáticamente el orden de creación.

##### `versions.tf` — restricciones de tooling

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.53.0"
    }
  }
}
```

Declara qué versiones de Terraform y providers necesita el module:
- `required_version`: el binario `terraform` debe ser >= 1.9. Si tienes 1.8, falla `init`.
- `required_providers`: declara qué providers usa. El `~> 6.53.0` permite parches `6.53.x` pero no salta a 6.54+ sin commit explícito.

Por qué archivo separado: para que un humano que abre el module **vea las versiones requeridas de un vistazo** sin scrollear `main.tf`. También facilita pin/upgrades centralizados.

### 5.3 `compositions/`

Una composition es una **receta que ensambla modules** para un arquetipo de workload concreto. La regla: **un archivo `.tf` por cada module enchufado** — para que sea trivial leer "qué tiene este arquetipo".

```
compositions/
├── agent-base/         # agente sin memory ni KB ni tools (el más simple)
├── agent-chatbot/      # agente conversacional con memory
├── agent-with-tools/   # agente con tools (gateway targets)
├── agent-with-kb/      # agente con knowledge base
├── mcp-server/         # MCP server expuesto via gateway
├── tool-lambda/        # tool aislada como Lambda
└── gateway-deploy/     # deploy de un gateway custom (no default)
```

Ejemplo: [`compositions/agent-with-tools/`](../Infra-AgentCore/compositions/agent-with-tools/):

```
compositions/agent-with-tools/
├── main.tf               # solo terraform{} + provider + locals (ZERO recursos)
├── variables.tf          # inputs (proyectados del manifest)
├── outputs.tf            # outputs hacia el deployable
├── runtime.tf            # module "runtime"
├── runtime_role.tf       # module "runtime-role" (custom IAM role opcional)
├── memory.tf             # module "memory"
├── gateway_targets.tf    # module "gateway-target" (for_each)
├── gateway_policies.tf   # module "gateway-policy"
└── observability.tf      # module "observability"
```

#### Paso 1: el `main.tf` declara el "frame" (sin recursos)

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.53.0" }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  runtime_name = "${var.name}-${var.environment}"
  base_tags    = { for t in var.tags : t => "true" }
}
```

`main.tf` en una composition **no crea recursos** — solo configura terraform/provider y define `locals` reutilizables. Si quieres saber qué recursos crea una composition, abres uno de los otros archivos `*.tf`.

#### Paso 2: cada `<componente>.tf` invoca un module

```hcl
# runtime.tf
module "runtime" {
  source = "../../modules/runtime"

  name        = local.runtime_name
  role_arn    = local.effective_runtime_role_arn
  image_uri   = var.image_uri
  env_vars    = var.runtime.env
  memory_id   = module.memory.memory_id   # ← cross-module wiring
  pipeline_id = var.pipeline_id
  tags        = local.base_tags
  models      = var.models
}
```

Cada bloque `module "X"` es una **invocación**:
- `source`: ruta relativa al module (`../../modules/runtime`)
- Después, mapeás cada **variable** del module a un valor: `var.X` (del manifest), `local.X` (computado), o `module.Y.Z` (output de otro module → wiring)

El `memory_id = module.memory.memory_id` es wiring clave: terraform infiere que `module.runtime` depende de `module.memory` y los crea en orden.

#### Paso 3: features opcionales con `count`

```hcl
# observability.tf
module "observability" {
  count  = lookup(var.features, "enable_observability", true) ? 1 : 0
  source = "../../modules/observability"
  ...
}
```

Si el manifest declara `features.enable_observability: false`, ese module **no se crea**. Permite arquetipos flexibles: la misma composition puede tener observability sí o no.

#### Paso 4: múltiples instancias con `for_each`

```hcl
# gateway_targets.tf
module "gateway_targets" {
  for_each = { for idx, t in var.gateway_targets : "${t.gateway}-${idx}" => t }
  source   = "../../modules/gateway-target"
  ...
}
```

Si el manifest declara 3 `gateway_targets`, terraform crea 3 instancias del module. Los accedés como `module.gateway_targets["oauth-3lo-0"].target_id`.

#### Paso 5: `outputs.tf` expone lo que el deployable consume

```hcl
output "agent_runtime_arn" { value = module.runtime.agent_runtime_arn }
output "memory_id"         { value = module.memory.memory_id }
```

El deployable lee estos outputs después del apply, los persiste, los muestra en logs del pipeline, etc.

#### Paso 6: `variables.tf` — el contrato con el deployable

Declara qué espera la composition. El **deployable** la llena con un `terraform.auto.tfvars.json` generado del `manifest` del workload + el `env-defaults.yaml` del ambiente. Ver siguiente sección.

#### Por qué un archivo por module en la composition

Cuando creas un nuevo arquetipo (ej: `agent-with-rag-and-tools`), lo más fácil es **copiar la composition más cercana** y agregar/quitar archivos `.tf`. No tienes que leer un `main.tf` gigante para entender qué piezas tiene. Si comparas `agent-base/` (3 archivos de modules) vs `agent-with-tools/` (6), la diferencia entre arquetipos es literalmente "qué archivos tiene".

---

## 6. Deployables

`iac/AgentCore/agentcore-{dev,qa,prd}` — **un repo deployable por ambiente**. Cada uno tiene:

```
agentcore-{env}/
├── .gitlab-ci.yml      # incluye Compose/agentcore/pipeline_infra.yml
├── README.md
├── env-defaults.yaml   # ⭐ valores específicos del ambiente
├── providers.tf        # configuración del provider (region, role_arn, kms key)
└── versions.tf         # constraints (igual que en Infra-AgentCore)
```

### `env-defaults.yaml` — los valores que NO vienen del manifest

Información que es propia del ambiente, no del workload:
- ARNs de los 3 gateways default (`oauth_3lo`, `oauth_2lo`, `sigv4_m2m`)
- ARN del KMS key de artefactos
- ARN del IAM role base `runtime-execution`
- ARN del bucket de artefactos
- VPC ID, subnet IDs, security group IDs
- Permission boundary ARN corporativo

Estos valores los renderiza el componente `render_tfvars` junto con los del manifest, produciendo el `terraform.auto.tfvars.json` final que terraform consume.

### State terraform — uno por workload por ambiente

Cada workload tiene su propio state terraform en S3. Convención de naming:
```
s3://{tf-state-bucket}/agentcore/{env}/{kind}/{capability}/{name}.tfstate
```

Esto significa que terraform destroy de un workload no afecta a otros workloads. Cada tfstate es independiente.

### Por qué deployables separados de Infra-AgentCore

El **código terraform** (modules + compositions) se versiona con tags semver en `Infra-AgentCore`. Los **deployables** apuntan a un tag específico via `INFRA_REF`. Esto permite:
- **Rollback de infra**: ante un bug en `Infra-AgentCore@v1.5.0`, los deployables siguen apuntando a `@v1.4.9` hasta que se valide la fix.
- **Dev/QA/PRD pueden estar en versiones distintas**: dev ya migró a `v1.5.0`, prd sigue en `v1.4.9` mientras se valida.
- **Auditoría**: el state file del deployable tiene metadata de qué tag se usó.

---

## 7. Flujo end-to-end

Aquí unifico todo. Tomemos el caso típico: un dev de capability modifica el manifest de un agente y pushea a `dev`.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 1. EVENT — git push a AgentPlatform/agents/customer-support/chatbot-tier1/   │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 2. AgentPlatform/.gitlab-ci.yml detecta el cambio por path                   │
│    rules: changes: agents/**/* → incluye Compose/pipeline_deploy_agents.yml  │
│    Variables resueltas: WORKLOAD_PATH, CAPABILITY, WORKLOAD_NAME             │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 3. Compose-AgentCore/pipeline_deploy_agents.yml ejecuta los stages:          │
│                                                                              │
│    .pre               → componente pipeline_telemetry → emite TRACE_ID       │
│    validate           → componente validate_manifest (JSON-schema)           │
│                       → componente validate_structure (cross-validation)     │
│    package            → componente package_artifact                          │
│                         (zipea src/ + sube a s3://artifacts-dev-.../...zip)  │
│    build              → componente build_image                               │
│                         (docker buildx --platform linux/arm64 → ECR)         │
│    scan               → componente scan_image (Trivy gate; falla si HIGH+)   │
│    secrets            → componente upload_secret (CI vars → Secrets Mgr)     │
│    publish-prompts    → componente publish_prompt (Bedrock Prompt Mgmt)      │
│    render             → componente apply_policy (.cedar → JSON)              │
│                       → componente render_tfvars                             │
│                         (manifest + env-defaults → terraform.auto.tfvars)    │
│    deploy             → componente trigger_iac (multi-project trigger)       │
│                                                                              │
│    Output del trigger: TFVARS_JSON, COMPOSITION_NAME, INFRA_REF              │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼  multi-project trigger
┌──────────────────────────────────────────────────────────────────────────────┐
│ 4. iac/AgentCore/agentcore-dev/.gitlab-ci.yml (downstream)                   │
│    incluye Compose/pipeline_infra.yml                                        │
│                                                                              │
│    .prepare:                                                                 │
│      - git clone Infra-AgentCore@${INFRA_REF} → /tmp/infra                   │
│      - cp /tmp/infra/compositions/${COMPOSITION_NAME} compositions/...       │
│      - cp /tmp/infra/modules modules/                                        │
│      - echo "${TFVARS_JSON}" > .../terraform.auto.tfvars.json                │
│      - cp env-defaults.yaml .../env-defaults.yaml                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 5. terraform init/plan/apply en compositions/{COMPOSITION_NAME}/             │
│                                                                              │
│    terraform init  → descarga hashicorp/aws ~> 6.53.0                        │
│                    → carga state desde S3                                    │
│    terraform plan  → calcula diff entre state y .tf + tfvars                 │
│    terraform apply → invoca AWS APIs:                                        │
│                       module.runtime    → aws_bedrockagentcore_agent_runtime │
│                       module.memory     → aws_bedrockagentcore_memory        │
│                       module.observability → aws_cloudwatch_log_group + ...  │
│                                                                              │
│    Outputs persistidos en el job: agent_runtime_arn, memory_id, etc.         │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼  vuelve al pipeline upstream
┌──────────────────────────────────────────────────────────────────────────────┐
│ 6. smoke stage: componente smoke_test                                        │
│    invoca POST agent_runtime_arn/ping                                        │
│    valida que devuelve 200 OK con shape esperado                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ 7. .post stage: pipeline_telemetry → emite end con duración + status         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Qué pasa en cada promoción

| Branch | AWS Account | Approval | Lo que cambia |
|--------|-------------|----------|---------------|
| `dev` | `dev-agenticplatform` | automático | Mismo flujo, env=dev, role limitado a dev |
| `qa` (MR de dev) | `qa-agenticplatform` | manual approval | env=qa, role distinto, runners separados |
| `main` + tag `vX.Y.Z` | `prd-agenticplatform` | manual approval + CAB | env=prd, role con permission boundary, drift checks activos |

### Qué pasa en rollback

Editás el manifest del workload con la versión previa del runtime (o un tag de imagen anterior), haces push. El pipeline detecta el cambio, hace todo el flujo de nuevo, y terraform crea una versión nueva del runtime apuntando a la imagen vieja. El concepto de "alias live" (que apunta a la versión activa) hace que los callers no necesiten cambiar nada.

### Qué NO toca el pipeline

Cosas que solo se modifican manualmente con permisos elevados:
- Recursos de `foundation/bootstrap/` (KMS keys, S3 buckets, IAM roles base)
- Recursos de `foundation/default-gateways/` (los 3 gateways por ambiente)
- Recursos de `foundation/vpc-endpoints/`

Estos viven en pipelines separados (`pipeline_foundation.yml`) que requieren approval explícito de plataforma. Nunca se tocan por commits a `AgentPlatform`.

---

## Referencias rápidas

- Manifest schema: `Componentes-AgentCore/config_files/validate_manifest/manifest.schema.json`
- Manifest reference: [`MANIFEST_REFERENCE.md`](../MANIFEST_REFERENCE.md)
- Plan global y fases: [`PLAN.md`](../PLAN.md)
- Multi-account: [`MULTI_ACCOUNT.md`](../MULTI_ACCOUNT.md)
- Runbook de destroy en PRD: [`RUNBOOK_DESTROY_PRD.md`](../RUNBOOK_DESTROY_PRD.md)
- Variables CI: [`CI_VARIABLES.md`](../CI_VARIABLES.md)
- Quotas AWS: [`07_QUOTAS.md`](07_QUOTAS.md)
- Diagramas de flujo: [`05_FLOWS_AND_DIAGRAMS.md`](05_FLOWS_AND_DIAGRAMS.md)
- Architecture components: [`04_ARCHITECTURE_COMPONENTS.md`](04_ARCHITECTURE_COMPONENTS.md)
