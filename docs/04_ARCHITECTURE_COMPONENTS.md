# Arquitectura de Componentes

> Cómo funcionan las distintas piezas (componentes CI, compose, módulos TF, composiciones) y por qué están separadas.

## Modelo mental: "cómo / cuándo / qué"

La separación raíz del framework responde tres preguntas distintas:

| Pregunta | Responsabilidad | Vive en |
|---|---|---|
| **¿Cómo hacer algo?** | Lógica reusable, agnóstica del contexto | `Componentes-AgentCore/` |
| **¿Cuándo, dónde y con qué hacerlo?** | Orquestación, rules, contexto productivo | `Compose-AgentCore/` |
| **¿Qué hacer?** | Código del workload (agente/MCP/tool) + manifest declarativo | `AgentPlatform/` |
| **Infraestructura subyacente** | Recursos AWS modelados en Terraform | `Infra-AgentCore/` + `iac/AgentCore/` |

Si en algún momento alguien pone lógica de "cuándo" en un componente, o lógica de "cómo" en compose, está rompiendo la separación. Eso se detecta en code review.

---

## 1. Componentes CI (`Componentes-AgentCore/`)

### Anatomía de un componente

```
Componentes-AgentCore/
├── templates/
│   └── <subdominio>/
│       └── template.yml           ← consumible vía include: - component:
├── src/
│   └── <subdominio>/
│       └── <action>.py            ← lógica Python (ejecutada por el job)
└── config_files/
    └── <subdominio>/              ← YAMLs/JSONs de configuración (no de pipeline)
```

**Simetría triple obligatoria:** templates ↔ src ↔ config_files con mismo nombre de subdominio. Cualquier inconsistencia rompe el pull dinámico de `pull_python_scripts_dominio.yml`.

### Reglas duras del framework

- **Inputs tipados con `spec.inputs` y separador `---`** en cada `template.yml`.
- **NO** `rules`, `tags`, `default:` global, ni `workflow:` en componentes (eso vive en compose).
- **Nombres dinámicos de jobs** vía `"$[[ inputs.job_name ]]"` (evita colisiones cuando un componente se incluye múltiples veces).
- **Lógica en Python**, no bash inline. Bash solo via `!reference` para boilerplate (auth AWS, descarga de scripts).
- **`description` y `default`** en cada input (incluso comillas vacías para opcionales).

### Anatomía interna del runner

Cuando un componente se incluye desde el compose:

1. GitLab descarga el `template.yml` del componente.
2. El template incluye `pull_python_scripts_dominio.yml` y `pull_config_files_dominio.yml` (que están en `templates/includes/base/`).
3. Esos `pull_*.yml` ejecutan `curl` con `GITLAB_TOKEN_READ_API` para descargar `src/<subdominio>/` y `config_files/<subdominio>/` al runner.
4. El job ejecuta `python python_scripts/<subdominio>/<action>.py`.
5. El script Python lee env vars (que vienen de los `inputs` del componente) y produce artifacts (típicamente JSON files que el siguiente stage consume).

### Convenciones de outputs entre componentes

Cada componente que produce información para otros usa un JSON file con shape estable:

| Componente | Produce | Consumido por |
|---|---|---|
| `package_artifact` | `artifact_meta.json` | `render_tfvars` |
| `build_image` | `image_meta.json` | `render_tfvars` |
| `upload_secret` | `secret_meta.json` | (consultado para audit) |
| `publish_prompt` | `prompt_arns.json` | `render_tfvars` (inyecta como env vars) |
| `apply_policy` | `cedar_policies.json` | `render_tfvars` |
| `render_tfvars` | `terraform.auto.tfvars.json` + `composition_name.txt` | `trigger_iac` |
| `pipeline_telemetry` (start) | `telemetry.env` (con `TRACE_ID=...`) | Todos los stages siguientes |

Esta cadena explícita es la que el componente `validate_structure` valida en parte: que no haya un componente esperando un input que ningún otro produce.

### Cómo agregar un componente nuevo

1. Crear `templates/<nuevo>/template.yml` con `spec.inputs` + `---`.
2. Crear `src/<nuevo>/<action>.py` con la lógica.
3. Si necesita YAMLs/JSONs de config, crear `config_files/<nuevo>/`.
4. Agregar tests pytest en `tests/unit/test_<nuevo>.py`.
5. Documentar en `MANIFEST_REFERENCE.md` y este documento.
6. Tag semver `vX.Y.Z` en `Componentes-AgentCore`.
7. Compose puede consumirlo con `@vX.Y.Z` o `@main`.

---

## 2. Compose (`Compose-AgentCore/`)

### Qué hay y qué no

**HAY:**
- Pipelines productivos (`pipeline_*.yml`) con `stages`, `include: - component:`, `default`, `workflow`.
- Reglas de promoción dev→qa→prd (`rules/branch-to-env.yml`).
- Reglas de path-based triggers (`rules/paths.yml`).
- Manual approval gates (`rules/approvals.yml`).
- Variables por ambiente (`variables/env-{dev,qa,prd}.yml`).

**NO HAY:**
- Python.
- Lógica de negocio.
- Validaciones (eso lo hacen los componentes).
- Hardcoded model_ids, account_ids, ARNs (todo viene de CI variables o env-defaults).

### Cómo se compone un pipeline

```yaml
# pipeline_deploy_agents.yml
stages: [.pre, validate, package, build, ..., .post]

include:
  - local: rules/branch-to-env.yml
  - local: variables/env-dev.yml
  - component: $CI_SERVER_FQDN/Componentes/agentcore/validate_manifest@main
    inputs: { job_name: validate-manifest, stage: validate, ... }
  - component: $CI_SERVER_FQDN/Componentes/agentcore/package_artifact@main
    inputs: { ... }
  # ... más componentes

# rules y orden explícito (needs:) viven SOLO acá
render-tfvars:
  needs: [validate-manifest, package-artifact, build-image, scan-image, publish-prompts, apply-policy]
```

### Cuándo crear pipeline nuevo en Compose

Cuando aparezca un caso de uso fundamentalmente distinto. Por ejemplo:
- `pipeline_deploy_agents.yml`: workload tipo agente.
- `pipeline_deploy_mcps.yml`: workload tipo MCP server.
- `pipeline_drift_detection.yml`: scheduled, no triggereado por commits.
- `pipeline_infra_tests.yml`: tests del repo Infra-AgentCore.

**No crear pipeline nuevo solo por tener una variante** (ej: chatbot vs no-chatbot). Eso se resuelve con composiciones distintas dentro del mismo pipeline.

### Versionado y consumo

- `Compose-AgentCore` se versiona con tags semver (`v1.0.0`, `v1.1.0`).
- El repo `AgentPlatform` y los deployables `agentcore-{env}` consumen pipelines via:
  ```yaml
  include:
    - project: Componentes/Compose/agentcore
      ref: v1.2.0   # o main
      file: pipeline_deploy_agents.yml
  ```

---

## 3. Módulos Terraform (`Infra-AgentCore/modules/`)

### Anatomía estándar

```
modules/<nombre>/
├── main.tf         ← los resources
├── variables.tf    ← inputs tipados con descriptions y validations
├── outputs.tf      ← outputs reutilizables
└── versions.tf     ← required_version + required_providers
```

Esta estructura es **canónica**. Todo módulo cumple los 4 archivos. Eso permite testing, documentación auto-generable, y consumo via `git::` con cualquier ref.

### Filosofía de los módulos

- **Atómicos:** un módulo modela un recurso o componente AgentCore. `runtime`, `memory`, `gateway-target` etc. **No** módulos "hacelo-todo".
- **Sin estado interno:** los módulos no asumen contexto. Reciben todo via variables, devuelven todo via outputs.
- **Backwards compatible:** agregar una variable opcional con default razonable es OK. Quitar/renombrar es breaking → bump major.
- **Stateless desde el punto de vista del state TF:** los módulos no tienen state propio. El state lo gestiona el deployable que los invoca.

### Convención: un recurso "core" + recursos auxiliares

Ejemplo `modules/runtime/`:
- `aws_bedrockagentcore_agent_runtime.this` — recurso core
- `aws_bedrockagentcore_agent_runtime_version.v` — auxiliar (versionado)
- `aws_bedrockagentcore_agent_runtime_alias.live` — auxiliar (alias 'live')

Esto refleja la unidad lógica: un "runtime" es runtime + version + alias todos juntos. Separarlos en 3 módulos sería sobreingeniería.

### Cómo agregar un módulo nuevo

1. Crear directorio `modules/<nuevo>/`.
2. Definir `variables.tf` con inputs claros (incluyendo `validation` blocks para reglas).
3. Definir `main.tf` con los recursos AWS (o `null_resource` con `local-exec` cuando el provider no expone el recurso, como `gateway-policy`).
4. Definir `outputs.tf` con todo lo que las composiciones pueden necesitar.
5. Definir `versions.tf` con pin del provider AWS.
6. Agregar tests `tests/*.tftest.hcl` con `command = plan`.
7. Documentar en `MANIFEST_REFERENCE.md` (tabla de módulos).
8. Tag semver y release.

### Issues conocidos del provider AWS Terraform

| Issue | Recurso | Workaround |
|---|---|---|
| #46128 | `aws_bedrockagentcore_gateway_target` no expone `grant_type` para OAuth | `null_resource` + `local-exec` con AWS CLI |
| #45099 | `aws_bedrockagentcore_agent_runtime` deja ENIs huérfanas en destroy | Documentado en `RUNBOOK_DESTROY_PRD.md` |
| (sin issue) | No existe `aws_bedrockagentcore_policy_engine` | `null_resource` + CLI `agentcore` (módulo `gateway-policy`) |

**Política:** vigilar releases del provider trimestralmente, migrar a recursos nativos cuando estén disponibles. El flag `use_native_resource` está reservado en los módulos para esa migración.

---

## 4. Composiciones Terraform (`Infra-AgentCore/compositions/`)

### Qué son

Una composición es un **ensamble curado** de módulos para un arquetipo concreto. Es lo que el deployable invoca con `module "this" { source = ".../compositions/<nombre>" }`.

### Anatomía: un archivo `.tf` por componente enchufado

```
compositions/agent-with-kb/
├── main.tf               ← terraform/provider/locals (sin recursos)
├── runtime.tf            ← module "runtime"
├── memory.tf             ← module "memory"
├── knowledge_base.tf     ← module "knowledge_base"
├── observability.tf      ← module "observability" (con flag count)
├── runtime_role.tf       ← role custom opcional (count = local.has_runtime_iam)
├── variables.tf          ← inputs tipados
└── outputs.tf            ← outputs expuestos al deployable
```

Esta separación facilita 2 cosas:
1. **Leer una composición en 30 segundos** — los nombres de archivo dicen exactamente qué hay.
2. **Crear composición nueva copy/paste** — copiar la composición más cercana, agregar/borrar archivos `.tf` por componente.

### Las 7 composiciones existentes

| Composición | Archivos `.tf` (además de main/variables/outputs) | Cuándo usarla |
|---|---|---|
| `agent-base` | runtime, observability, runtime_role | Agente stateless |
| `agent-chatbot` | + memory | Chatbot conversacional simple |
| `agent-with-kb` | + knowledge_base | Agente con RAG |
| `agent-with-tools` | + memory + gateway_targets + gateway_policies | Agente con tools externas |
| `mcp-server` | runtime + oauth_provider + gateway_targets + gateway_policies + observability + runtime_role | MCP server detrás de gateway |
| `tool-lambda` | lambda + gateway_target | Tool standalone como Lambda |
| `gateway-deploy` | gateway + targets + policies | Gateway custom standalone (raro) |

### Patrón "opt-in" via flags y variables opcionales

Cada componente opcional dentro de una composición se controla con:
- **Variable presente** → componente se crea (ej: `var.gateway_targets[]` no vacío → módulo `gateway-target` se invoca con `for_each`)
- **Flag booleano** en `var.features.enable_X` (ej: `enable_observability`, `enable_policies`)
- **Bloque opcional** en variables (ej: `var.oauth_provider != null` → módulo OAuth se crea)

Esto es lo que permite que un workload **solo declare lo que necesita** sin que la composición falle por valores ausentes.

### Cuándo crear composición nueva vs extender existente

**Crear nueva** cuando:
- 3+ workloads piden el mismo combo no soportado.
- El combo requiere lógica que no calza con ninguna composición existente.

**Extender existente** cuando:
- Un workload pide un módulo opcional adicional → agregar archivo `.tf` con flag/count en la composición existente.
- Un módulo necesita variable nueva → agregar al módulo y propagar a composiciones que lo usen.

**No crear nueva por miedo a romper** una existente. La forma correcta es: extender + tests + tag.

---

## 5. Foundation (`Infra-AgentCore/foundation/`)

Recursos AWS que existen **una sola vez por cuenta** y soportan a todos los workloads.

### `bootstrap/`
- KMS keys (artifacts, secrets) con rotación
- S3 artifact buckets (3: agents, mcp, tools) con lifecycle a Glacier
- IAM role base `<env>-runtime-execution`
- En PRD: IAM Deny policy para `bedrock-agentcore:Delete*` + `agentcore-prd-emergency-destroyer` role

### `default-gateways/`
- 3 gateways AgentCore por defecto del ambiente:
  - `oauth-3lo` (human-machine, JWT con scopes openid/profile)
  - `oauth-2lo` (machine-machine OAuth con client_credentials)
  - `sigv4-m2m` (machine-machine SigV4)

### `vpc-endpoints/`
- Endpoints VPC privados: bedrock-runtime, bedrock-agent-runtime, ECR, S3, Secrets Manager, Logs, STS

**Política:** `foundation/` se aplica manualmente por el equipo de plataforma una sola vez por cuenta. NO se aplica desde pipelines de workloads.

---

## 6. Deployables (`iac/AgentCore/agentcore-{env}`)

### Por qué proyectos GitLab separados (no carpetas)

GitLab managed Terraform state es **per-project**. Para tener state aislado por ambiente/shard, cada deployable es un proyecto GitLab independiente.

### Qué hay en un deployable

```
agentcore-{env}/
├── .gitlab-ci.yml         ← include de pipeline_infra.yml
├── env-defaults.yaml      ← account_id, VPC, KMS, role_arn, gateway_ids, etc.
├── providers.tf           ← provider aws con assume-role a la cuenta
├── versions.tf            ← backend "http" (GitLab managed state)
└── README.md
```

**No hay módulos ni composiciones aquí.** El deployable solo tiene tfvars + provider config + state. La composition la baja vía `git::` con tag pinneado de `Infra-AgentCore` cuando el pipeline corre.

### Cómo se ejecuta una composition desde un deployable

1. Pipeline upstream (en `AgentPlatform`) genera `terraform.auto.tfvars.json` y `composition_name.txt`.
2. `trigger_iac` dispara el pipeline downstream del deployable correspondiente.
3. `pipeline_infra.yml` clona `Infra-AgentCore` en el ref especificado (típicamente un tag semver).
4. Copia `compositions/{composition_name}/` y `modules/` al working dir.
5. Inyecta el `terraform.auto.tfvars.json`.
6. `terraform init` con backend GitLab managed state (state name único por workload).
7. `terraform plan` → manual gate (en QA/PRD) → `terraform apply`.

### State naming

Convención: `agentcore-{env}-{composition}-{upstream_project_path_slug}`.

Ejemplo: `agentcore-prd-agent-with-kb-ia-generativa-agentplatform-agents-finance-ledger-bot`.

Esto garantiza que cada workload tiene su propio state file, evitando que dos workloads colisionen en el mismo state.

---

## Decisiones arquitectónicas clave

### 1. Separación de repos (8 repos en lugar de monorepo)

**Por qué:** ciclos de vida distintos (componentes cambian más que módulos TF, workloads cambian más que componentes), permisos distintos por repo, ownership claro.

**Costo:** mayor overhead de governance al crear repos nuevos, MRs cross-repo.

### 2. Composición vs flags vs jinja-render de HCL

**Decisión:** composiciones predefinidas con flags booleanos para opcionales. **NO** generación dinámica de HCL.

**Por qué:** `terraform plan` debe ser revisable. HCL generado dinámicamente es ilegible y dificulta auditoría.

### 3. GitLab-managed state vs S3 backend

**Decisión:** GitLab-managed state, un proyecto por deployable.

**Por qué:** locking + versioning automáticos, audit nativo, no hay que mantener bucket de state aparte. Costo: state files no portables a otros sistemas CI sin migración.

### 4. Componentes CI con descarga dinámica de scripts

**Decisión:** scripts Python en `src/` se descargan en runtime via `pull_python_scripts_dominio.yml` (curl con GitLab token).

**Por qué:** componente es solo el `template.yml` (lo que GitLab indexa); todo lo demás se baja del repo. Permite versionar scripts sin tener que re-publicar el componente.

**Costo:** dependencia de GitLab token con scope `read_api`. Si cambia, todos los pipelines fallan hasta rotar.

### 5. Modelos y prompts como artefactos auditables (no hardcoded)

**Decisión:** modelos en `spec.models[]`, prompts en `spec.prompts[]`. Ambos referenciados por alias en código.

**Por qué:** simetría de cambio. Cambiar modelo o prompt = MR al manifest = audit trail. Cambiar código = MR al repo del agente.

**Costo:** 1 nivel de indirección que el dev tiene que entender (env vars vía alias).

### 6. Default seguro por defecto

**Ejemplos:**
- Cedar policies: `LOGONLY` por default (shadow mode).
- Severity threshold scan: `HIGH` por default.
- `attach_bedrock_invoke`: `true` por default (90% de runtimes lo necesitan).
- Manual gates en QA/PRD por default.
- Manual gate adicional para destroys en PRD.

**Por qué:** equivocarse hacia "más seguro pero menos performante" es preferible a "menos seguro" en organización regulada.
