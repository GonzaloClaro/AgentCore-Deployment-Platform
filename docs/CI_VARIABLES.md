# CI/CD Variables y Configuración

> **Lugar único de la verdad** para todas las variables de entorno, secretos y valores de configuración que la plataforma AgentCore necesita. Si vas a configurar GitLab por primera vez, este es el documento que tienes que seguir.

## Índice

1. [Convenciones](#convenciones)
2. [Variables a nivel **GitLab Group**](#1-variables-a-nivel-gitlab-group)
3. [Variables por proyecto deployable (`iac/AgentCore/agentcore-{env}`)](#2-variables-por-proyecto-deployable-iacagentcoreagentcore-env)
4. [Variables del repo de workloads (`AgentPlatform`)](#3-variables-del-repo-de-workloads-agentplatform)
5. [Valores en `env-defaults.yaml` (no son CI variables)](#4-valores-en-env-defaultsyaml)
6. [Resumen tabular: dónde configurar qué](#5-resumen-tabular)
7. [Checklist de bootstrap inicial](#6-checklist-de-bootstrap-inicial)

---

## Convenciones

- **Masked**: la variable no aparece en logs (✅ activar para todo lo que sea secreto/token).
- **Protected**: la variable solo está disponible en branches/tags protegidos (✅ activar para credenciales de QA/PRD).
- **Scope = environment**: la variable solo está disponible cuando el job declara ese `environment:` (clave para separar credenciales por ambiente).
- **File type**: la variable se monta como archivo en el runner (útil para certs, kubeconfigs).

Convención de naming: `<NOMBRE>_<AMBIENTE>` para credenciales por ambiente (ej: `AWS_ROLE_ARN_DEV`).

---

## 1. Variables a nivel **GitLab Group**

Configurar en `Group → Settings → CI/CD → Variables`. Estas se heredan por todos los proyectos del grupo.

### 1.1 Group `Componentes/`
*(repo `Componentes/agentcore` y futuros componentes de otros dominios)*

| Variable | Tipo | Descripción |
|---|---|---|
| _Ninguna por ahora_ | — | Los componentes son agnósticos y no necesitan secretos al "publicarse"; solo cuando son consumidos. |

### 1.2 Group `Componentes/Compose/`
*(repo `Compose/agentcore`)*

| Variable | Masked | Protected | Descripción |
|---|---|---|---|
| `ORG_RUNNER_IMAGE` | ❌ | ❌ | URI de la imagen Docker del runner organizacional (ej: `internal-registry/runners/python-aws:1.0`). Usada como `IMAGE_BASE` en los jobs. |
| `GITLAB_TOKEN_READ_API` | ✅ | ✅ | Group access token con scope `read_api`, usado por `pull_python_scripts_dominio.yml` y `pull_config_files_dominio.yml` para clonar `Componentes/agentcore` desde los runners. |

### 1.3 Group `ia-generativa/`
*(repo `AgentPlatform`)*

| Variable | Masked | Protected | Scope | Descripción |
|---|---|---|---|---|
| `LEANIX_ENDPOINT` | ❌ | ❌ | * | URL del API de LeanIX (ej: `https://app.leanix.net/services/api/v1`). |
| `LEANIX_API_TOKEN` | ✅ | ✅ | `prd` | Bearer token de LeanIX. Solo necesario en branch `main`. |

### 1.4 Group `iac/AgentCore/`
*(repos `infra-agentcore` y los 3 deployables `agentcore-{env}`)*

| Variable | Masked | Protected | Scope | Descripción |
|---|---|---|---|---|
| `AWS_ROLE_ARN_DEV` | ✅ | ❌ | `dev` | Role IAM en cuenta `dev-agenticplatform` que asume el pipeline. |
| `AWS_ROLE_ARN_QA` | ✅ | ✅ | `qa` | Role IAM en cuenta `qa-agenticplatform`. |
| `AWS_ROLE_ARN_PRD` | ✅ | ✅ | `prd` | Role IAM en cuenta `prd-agenticplatform`. |
| `AWS_ACCOUNT_ID_DEV` | ❌ | ❌ | `dev` | Account ID DEV (12 dígitos). Usado en patrones de ARN. |
| `AWS_ACCOUNT_ID_QA` | ❌ | ✅ | `qa` | Account ID QA. |
| `AWS_ACCOUNT_ID_PRD` | ❌ | ✅ | `prd` | Account ID PRD. |

> 💡 **Recomendación**: configurar estas variables a **nivel de group `iac/AgentCore/`**, no por proyecto. Así los 3 deployables las heredan automáticamente. El scope por `environment` ya las separa correctamente.

---

## 2. Variables por proyecto deployable (`iac/AgentCore/agentcore-{env}`)

Generalmente NO hace falta configurar nada a nivel de proyecto deployable — todo se hereda del group `iac/AgentCore/`. La excepción es si quieres un **token de proyecto específico** o un override.

---

## 3. Variables del repo de workloads (`AgentPlatform`)

Solo lo específico de workloads que usan secretos OAuth (típicamente MCP servers). Configurar a **nivel de proyecto** en GitLab → `AgentPlatform → Settings → CI/CD → Variables`, con scope por environment.

| Variable | Masked | Protected | Scope | Descripción |
|---|---|---|---|---|
| `OAUTH_CLIENT_ID` | ❌ | ❌ | `dev`, `qa`, `prd` | Client ID OAuth del IdP corporativo (uno por ambiente). Usado por el componente `upload_secret`. |
| `OAUTH_CLIENT_SECRET` | ✅ | ✅ (qa/prd) | `dev`, `qa`, `prd` | Client Secret correspondiente. Se sube a Secrets Manager por `upload_secret`. |

> ⚠️ Si tienes múltiples MCPs/agentes con OAuth distintos, usa naming `OAUTH_CLIENT_SECRET_<NOMBRE>` y referencia desde el manifest.

---

## 4. Valores en `env-defaults.yaml`

Estos NO son CI variables — son configuración del ambiente que vive en `iac/AgentCore/agentcore-{env}/env-defaults.yaml` y se commitea al repo (no son secretos). Edítalos directamente en cada deployable.

| Campo | Ejemplo | De dónde sale |
|---|---|---|
| `account_id` | `123456789012` | Tu cuenta AWS DEV/QA/PRD |
| `vpc_id` | `vpc-0abc123` | VPC creada en la cuenta (foundation) |
| `subnet_ids` | `[subnet-aaa, subnet-bbb]` | Subnets privadas para el runtime |
| `kms_key_arn` | `arn:aws:kms:...:alias/agentcore-dev-artifacts` | Output de `foundation/bootstrap` |
| `default_role_arn` | `arn:aws:iam::...:role/agentcore-dev-runtime-execution` | Output de `foundation/bootstrap` |
| `default_gateway_ids.oauth_3lo` | `gw-...` | Output de `foundation/default-gateways` |
| `default_gateway_ids.oauth_2lo` | `gw-...` | Output de `foundation/default-gateways` |
| `default_gateway_ids.sigv4_m2m` | `gw-...` | Output de `foundation/default-gateways` |
| `s3_artifact_buckets.{agents,mcp,tools}` | `artifacts-dev-agentcore-agents` | Output de `foundation/bootstrap` |

Los placeholders `REPLACE_WITH_*` indican dónde tienes que pegar el valor real después de aplicar el `foundation/`.

---

## 5. Resumen tabular

> Dónde configurar qué, en formato leíble.

| Donde | Qué | Quién la consume |
|---|---|---|
| Group `Componentes/Compose` | `ORG_RUNNER_IMAGE`, `GITLAB_TOKEN_READ_API` | Todos los pipelines (templates de componentes) |
| Group `iac/AgentCore` | `AWS_ROLE_ARN_*`, `AWS_ACCOUNT_ID_*` (scope por env) | Pipelines de los 3 deployables |
| Group `ia-generativa` | `LEANIX_ENDPOINT`, `LEANIX_API_TOKEN` | Pipeline de catalog (solo branch main) |
| Project `AgentPlatform` | `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` (scope por env) | Componente `upload_secret` cuando hay MCP con OAuth |
| File `agentcore-{env}/env-defaults.yaml` | Account ID, VPC, subnets, KMS, role ARN, gateway IDs | `render_tfvars` (componente CI) y composiciones Terraform |

---

## 6. Checklist de bootstrap inicial

Sigue este orden la primera vez que armas la plataforma desde cero:

### Fase A: AWS por cuenta (dev/qa/prd)

- [ ] Crear las 3 cuentas AWS (`dev-agenticplatform`, `qa-agenticplatform`, `prd-agenticplatform`).
- [ ] En cada cuenta, crear un **role IAM para deploy** (`agentcore-{env}-deployer`) con trust hacia GitLab OIDC y permisos para Bedrock + ECR + S3 + KMS + IAM (mínimos).
- [ ] Anotar los 3 ARNs.

### Fase B: GitLab — variables CI/CD

- [ ] En el group `iac/AgentCore/`, crear las variables `AWS_ROLE_ARN_DEV`, `AWS_ROLE_ARN_QA`, `AWS_ROLE_ARN_PRD` (masked, scope = environment correspondiente).
- [ ] En el group `iac/AgentCore/`, crear `AWS_ACCOUNT_ID_DEV/QA/PRD`.
- [ ] En el group `Componentes/Compose/`, crear `ORG_RUNNER_IMAGE` y `GITLAB_TOKEN_READ_API`.
- [ ] En el group `ia-generativa/`, crear `LEANIX_ENDPOINT` y `LEANIX_API_TOKEN` (este último con scope `prd`).

### Fase C: Apply de foundation por cuenta

Para cada ambiente (dev → qa → prd):

- [ ] Aplicar `Infra-AgentCore/foundation/bootstrap/` con `terraform apply -var environment=<env>`.
- [ ] Tomar los outputs (KMS arns, S3 bucket names, runtime role ARN).
- [ ] Aplicar `Infra-AgentCore/foundation/default-gateways/` con los discovery URLs del IdP corporativo.
- [ ] Tomar los outputs (3 gateway IDs).
- [ ] (Opcional) Aplicar `foundation/vpc-endpoints/` si los runtimes corren en VPC privada.

### Fase D: Poblar `env-defaults.yaml` por deployable

Para cada `iac/AgentCore/agentcore-{env}/env-defaults.yaml`:

- [ ] Reemplazar todos los `REPLACE_WITH_*` con los valores reales (account_id, vpc_id, subnets, kms arn, role arn, gateway IDs, bucket names).
- [ ] Commit y push (no son secretos).

### Fase E: Smoke con un workload trivial

- [ ] Crear `AgentPlatform/agents/sandbox/hello-world/` copiando `agents/_template/`.
- [ ] Implementar un `agent.py` que solo devuelva `"hello"`.
- [ ] Push a branch `dev`.
- [ ] Validar que el pipeline corre los 8 stages, el zip aparece en S3, la imagen aparece en ECR, el runtime ARN existe y `aws bedrock-agentcore invoke-agent-runtime` responde.

### Fase F: Promover a QA/PRD

- [ ] MR `dev` → `qa`. Manual approval. Verificar en cuenta QA.
- [ ] MR `qa` → `main` con tag `v0.1.0`. Manual approval. Verificar en cuenta PRD.
- [ ] Verificar que LeanIX recibió la fact sheet del agente.

---

## Apéndice: variables built-in que GitLab inyecta

Estas NO se configuran — vienen automáticamente. Solo para referencia:

- `CI_SERVER_HOST` — hostname de la instancia GitLab
- `CI_SERVER_FQDN` — FQDN para los `include: component:`
- `CI_PROJECT_PATH` — path del proyecto que corre el pipeline
- `CI_COMMIT_BRANCH` — branch del commit
- `CI_COMMIT_SHORT_SHA` — primer 8 chars del SHA (usado como image tag)
- `CI_PIPELINE_ID` — ID numérico del pipeline (usado en `pipeline_id` para versions Terraform)
- `CI_JOB_TOKEN` — token efímero del job (usado para multi-project triggers y backend GitLab state)
- `CI_JOB_JWT_V2` — JWT firmado del job (usado por `aws sts assume-role-with-web-identity`)
