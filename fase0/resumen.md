# Resumen de fase 0 — arquitectura interna

> Vista global de cómo encajan los 5 repos lógicos de fase 0. Para el tutorial paso a paso ver [`TUTORIAL.md`](TUTORIAL.md). Para el detalle del manifest ver [`MANIFEST_REFERENCE.md`](MANIFEST_REFERENCE.md).

## Visión general

Fase 0 reproduce el patrón del framework completo, simplificado a los 5 repos lógicos esenciales con scope reducido a deploy zip + Bedrock invocation. Sin Docker, sin tools, sin gateways custom.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  AgentPlatform              (workloads — agentes en zip + Python)        │
│  └─ commit en manifest.yaml dispara pipeline                             │
│         │                                                                 │
│         ▼ include                                                         │
│  Compose-AgentCore          (orquestador — pipelines minimal)            │
│  └─ define stages: validate → package → render → deploy → smoke          │
│         │                                                                 │
│         ▼ include: - component:                                           │
│  Componentes-AgentCore      (9 componentes Python reutilizables)         │
│  └─ valida, zipea, sube a S3, renderiza tfvars, dispara terraform        │
│         │                                                                 │
│         ▼ multi-project trigger                                           │
│  iac/AgentCore/agentcore-{dev|qa|prd}  (deployables — terraform state)   │
│  └─ corre terraform apply contra Infra-AgentCore                          │
│         │                                                                 │
│         ▼ source = "../../modules/X"                                      │
│  Infra-AgentCore            (Terraform — modules + 2 compositions)       │
│  └─ define los recursos AWS (modo zip, sin Docker)                       │
└──────────────────────────────────────────────────────────────────────────┘
```

| Repo lógico | Rol | Lenguaje | Cambios vs global |
|-------------|-----|----------|-------------------|
| `AgentPlatform` | Workloads (agentes en Python + zip) | Python + YAML | Sin MCP, sin tools, manifest simplificado |
| `Componentes-AgentCore` | Componentes CI/CD reutilizables | Python + YAML | 9 componentes (vs 13 del global) |
| `Compose-AgentCore` | Pipelines productivos | YAML | Pipeline minimal (sin stages de Docker/Cedar/LeanIX) |
| `Infra-AgentCore` | Terraform | HCL | 2 composiciones (vs 7), módulo runtime adaptado a zip mode |
| `iac/AgentCore/agentcore-{env}` | State Terraform por ambiente | YAML + tfvars | Idéntico al global (solo placeholders distintos) |

---

## 1. AgentPlatform

```
AgentPlatform/
├── .gitlab-ci.yml                       # trigger al pipeline_deploy_agents
└── agents/
    └── _template/
        ├── manifest.yaml                # schema simplificado (solo zip mode)
        └── src/
            ├── main.py                  # entrypoint Python — HTTP server :8080
            └── requirements.txt
```

**Idea clave**: el dev de capability copia `_template/` y edita 3 cosas:
1. `metadata.name` y `capability` en el manifest
2. La lógica del agente en `src/main.py`
3. Los modelos en `spec.models[]`

Push a `dev` → pipeline despliega automáticamente.

## 2. Componentes-AgentCore

9 componentes Python invocables vía `include: - component:` desde Compose:

| Subdominio | Acción | Responsabilidad |
|------------|--------|-----------------|
| `validate_manifest` | `validate.py` | Valida `manifest.yaml` contra JSON-schema simplificado de fase 0 |
| `validate_structure` | `validate.py` | Cross-validation: composition válida + entrypoint existe + modelos en allowlist |
| `package_artifact` | `package.py` | Zipea `src/` + sube a S3 → emite `artifact_meta.json` |
| `upload_secret` | `upload.py` | CI variable masked → AWS Secrets Manager (solo Azure key) |
| `publish_prompt` | `publish.py` | Registra prompt en Bedrock Prompt Management vía SDK |
| `render_tfvars` | `render.py` | manifest + env-defaults + artifact_meta → `terraform.auto.tfvars.json` con shape zip |
| `trigger_iac` | `trigger.py` | Multi-project trigger al deployable `agentcore-{env}` |
| `smoke_test` | `smoke.py` | Invoca `/ping` post-deploy |
| `pipeline_telemetry` | — | TRACE_ID + eventos start/end |

**Componentes excluidos** (vs global): `build_image`, `scan_image`, `apply_policy`, `publish_leanix`, `drift_check`, macros de deploy.

## 3. Compose-AgentCore

```
Compose-AgentCore/
├── pipeline_deploy_agents.yml           # cuando cambian agents/**
├── pipeline_infra.yml                   # downstream — corre terraform apply
├── pipeline_foundation.yml              # bootstrap por cuenta (uso ocasional)
├── rules/
│   ├── branch-to-env.yml                # dev/qa/prd según branch
│   ├── paths.yml                        # rules de cambios por path
│   └── approvals.yml                    # required approvals
└── variables/
    ├── env-dev.yml
    ├── env-qa.yml
    └── env-prd.yml
```

### Stages del `pipeline_deploy_agents.yml`

```
.pre              telemetry-start (genera TRACE_ID)
validate          validate-manifest + validate-structure
package           package-artifact (zip → S3)
secrets           upload-secret (solo si Azure model)
publish-prompts   publish-prompt (solo si spec.prompts[])
render            render-tfvars
deploy            trigger-iac → pipeline downstream en agentcore-{env}
smoke             smoke-test
.post             telemetry-end
```

Total: 9 stages, 7-12 minutos típicos.

## 4. Infra-AgentCore

```
Infra-AgentCore/
├── modules/                             # 11 módulos (todos del global)
├── compositions/
│   ├── agent-base-zip/                  # NUEVA: runtime + observability
│   └── agent-with-kb-zip/               # NUEVA: runtime + memory + KB + observability
├── foundation/
│   ├── bootstrap/                       # KMS + S3 + IAM role base
│   ├── default-gateways/                # 3 gateways AgentCore (opcional en fase 0)
│   └── vpc-endpoints/                   # tráfico privado (opcional)
└── scripts/tf-check.sh                  # fmt + validate harness
```

### Diferencia técnica clave: zip mode

El módulo `runtime` en fase 0 usa `code_configuration` del provider AWS:

```hcl
agent_runtime_artifact {
  code_configuration {
    entry_point = ["main.py"]
    runtime     = "PYTHON_3_13"
    code {
      s3 {
        bucket = "artifacts-dev-agentcore-agents"
        prefix = "agents/platform-test/hello-agent/abc123.zip"
      }
    }
  }
}
```

vs la versión global:

```hcl
agent_runtime_artifact {
  container_configuration {
    container_uri = "12345.dkr.ecr.us-east-1.amazonaws.com/agent:v1"
  }
}
```

### Las 2 composiciones

#### `agent-base-zip`

```
agent-base-zip/
├── main.tf                              # terraform/provider/locals
├── runtime.tf                           # module "runtime" (zip)
├── runtime_role.tf                      # module "runtime-role" (IAM custom opcional)
├── observability.tf                     # module "observability"
├── variables.tf
└── outputs.tf
```

**Recursos AWS creados**:
- 1× `aws_bedrockagentcore_agent_runtime` (con S3 zip)
- 1× `aws_iam_role` (runtime execution, opcional si runtime_iam declarado)
- 1× `aws_cloudwatch_log_group`

#### `agent-with-kb-zip`

Idéntico a `agent-base-zip` + 2 archivos extra:

```
agent-with-kb-zip/
├── ... (todo lo de agent-base-zip)
├── memory.tf                            # module "memory"
└── knowledge_base.tf                    # module "knowledge-base"
```

**Recursos AWS adicionales**:
- 1× `aws_bedrockagentcore_memory`
- 1× `aws_bedrockagent_knowledge_base`
- 1× `aws_s3vectors_vector_bucket`
- 1× `aws_s3vectors_index`

## 5. iac/AgentCore/agentcore-{env}

```
agentcore-{env}/
├── .gitlab-ci.yml                       # incluye pipeline_infra
├── env-defaults.yaml                    # vpc_id, subnet_ids, kms_key_arn, etc.
├── providers.tf
└── versions.tf
```

State Terraform vive **en este repo, no en Infra-AgentCore**. Cada workload tiene su propio tfstate dentro de la cuenta del environment.

---

## Flujo end-to-end de despliegue

```
1. dev edita AgentPlatform/agents/<cap>/<name>/manifest.yaml + main.py
   ↓
2. git push origin dev
   ↓
3. AgentPlatform/.gitlab-ci.yml detecta cambios bajo agents/**
   ↓
4. include de Compose/pipeline_deploy_agents.yml
   ↓
5. Stages corren en orden:
   • validate (manifest + structure)
   • package (zip + S3 → artifact_meta.json con s3_bucket/s3_key)
   • secrets (upload Azure key si aplica)
   • publish-prompts (registra prompts)
   • render (manifest + env-defaults + artifact_meta → tfvars con code_s3_bucket/code_s3_prefix)
   • deploy (multi-project trigger al deployable)
        ↓
6. Pipeline downstream en agentcore-{env}
   ↓
7. .prepare:
   • git clone Infra-AgentCore@<INFRA_REF>
   • cp compositions/{COMPOSITION_NAME} ← del manifest (agent-base-zip o agent-with-kb-zip)
   • cp modules/
   • escribe terraform.auto.tfvars.json
   ↓
8. terraform init/plan/apply
   • module "runtime" → aws_bedrockagentcore_agent_runtime con code_configuration
   • module "memory" + "knowledge_base" si composition es agent-with-kb-zip
   • module "observability" → CW log group + dashboard
   ↓
9. Vuelve al pipeline upstream
   ↓
10. smoke-test: invoca /ping del runtime → si 200 OK, deploy exitoso
   ↓
11. telemetry-end: cierra TRACE_ID
```

## Restricciones reconocidas

- **Solo Python 3.13** — para soportar otros runtimes hay que migrar a fase 1+ con container mode
- **Solo zip ≤ 250MB descomprimido** — restricción del provider AWS
- **Sin dependencias system-level** — solo paquetes pip-instalables
- **Sin tools custom** — los agentes son self-contained
- **Sin MCP server** — agentes solo invocables, no exponen API a otros agentes
- **Sin Cedar policies** — control de acceso vía IAM, no policy engine
- **Sin LeanIX catalog** — sin registro corporativo de workloads

Cuando cualquiera de estas restricciones empiece a doler, es el momento de migrar features específicas desde la versión global del framework.

## Documentos relacionados

- [`README.md`](README.md) — overview rápido
- [`MANIFEST_REFERENCE.md`](MANIFEST_REFERENCE.md) — diccionario completo del manifest
- [`CI_VARIABLES.md`](CI_VARIABLES.md) — variables CI/CD requeridas
- [`TUTORIAL.md`](TUTORIAL.md) — paso a paso de adopción
