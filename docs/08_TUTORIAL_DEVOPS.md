# Tutorial paso a paso para el equipo de plataforma

> Audiencia: ingenieros DevOps / Platform Engineers que van a **operar** la plataforma. No para devs de equipos consumidores (esos siguen `AgentPlatform/README.md`).

Este documento te lleva de cero a un agente desplegado y operativo en una cuenta AWS sandbox. Después cubre operación día a día, troubleshooting y onboarding de nuevos consumidores.

## Tabla de contenidos

1. [Prerequisitos](#1-prerequisitos)
2. [Setup del entorno local](#2-setup-del-entorno-local)
3. [Bootstrap inicial de una cuenta AWS](#3-bootstrap-inicial-de-una-cuenta-aws)
4. [Configuración del CI/CD](#4-configuración-del-cicd)
5. [Despliegue del primer agente](#5-despliegue-del-primer-agente)
6. [Verificación end-to-end](#6-verificación-end-to-end)
7. [Troubleshooting común](#7-troubleshooting-común)
8. [Operación día a día](#8-operación-día-a-día)
9. [Onboarding de nuevos equipos consumidores](#9-onboarding-de-nuevos-equipos-consumidores)
10. [Procedimientos de emergencia](#10-procedimientos-de-emergencia)

---

## 1. Prerequisitos

Antes de empezar, confirma que tienes acceso y conocimiento de los siguientes elementos.

### Accesos necesarios

| Recurso | Para qué | Cómo obtenerlo |
|---------|----------|----------------|
| Cuenta AWS sandbox o `dev` | Desplegar primero foundation, luego el agente | Solicitud al equipo de cloud corporativo |
| Permisos IAM `AdministratorAccess` (sandbox) o role con permisos suficientes para crear KMS, IAM, S3, ECR, Bedrock | Bootstrap inicial | Mismo equipo de cloud |
| GitLab access a los 5 repos: `AgentPlatform`, `Componentes-AgentCore`, `Compose-AgentCore`, `Infra-AgentCore`, `iac/AgentCore/agentcore-{env}` | Modificar configuración y disparar pipelines | Equipo de plataforma o GitLab admin |
| Acceso al IdP corporativo (Okta / Azure AD) con permiso para crear app registrations | Configurar OAuth para los gateways | Equipo de IAM corporativo |

### Conocimiento previo asumido

- Terraform / OpenTofu intermedio (modules, state, providers, lifecycle)
- AWS IAM, KMS, S3, ECR (operación básica)
- Docker (build, push, multi-platform images)
- GitLab CI/CD components y multi-project pipelines
- Conceptos de Bedrock AgentCore (runtime, gateway, memory, knowledge base) — leer `docs/04_ARCHITECTURE_COMPONENTS.md` antes

### Tooling local

Instala lo siguiente en tu máquina:

```bash
# macOS (con Homebrew)
brew install opentofu          # o terraform si ya lo tienes
brew install awscli
brew install gh                # GitHub CLI, opcional
brew install jq yq             # parsing de JSON/YAML
brew install pre-commit        # opcional, para hooks
brew install python@3.12

# Linux (Ubuntu/Debian)
# Sigue las guías oficiales:
# - OpenTofu: https://opentofu.org/docs/intro/install/
# - AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
```

Verifica versiones mínimas:

```bash
tofu version          # >= 1.9
aws --version         # >= 2.x
docker --version      # >= 24.x
python3 --version     # >= 3.12
```

---

## 2. Setup del entorno local

### 2.1 Clonar los repos

Para operar la plataforma necesitas los 5 repos lógicos en local. Si trabajas con la versión consolidada (monorepo de referencia):

```bash
git clone <url-del-monorepo> agentcore-platform
cd agentcore-platform
```

Si trabajas con los repos separados (estructura GitLab corporativa):

```bash
mkdir agentcore-platform && cd agentcore-platform
git clone <url>/AgentPlatform.git
git clone <url>/Componentes-AgentCore.git
git clone <url>/Compose-AgentCore.git
git clone <url>/Infra-AgentCore.git
git clone <url>/iac/AgentCore/agentcore-dev.git
```

### 2.2 Configurar credenciales AWS

Configura un perfil AWS para la cuenta sandbox o `dev`:

```bash
aws configure --profile agentcore-dev
# AWS Access Key ID:     <tu access key>
# AWS Secret Access Key: <tu secret>
# Default region:        us-east-1
# Default output:        json

# Verifica que funciona
export AWS_PROFILE=agentcore-dev
aws sts get-caller-identity
```

Salida esperada:
```json
{
    "UserId": "AIDA...",
    "Account": "111122223333",
    "Arn": "arn:aws:iam::111122223333:user/tu.usuario"
}
```

> **Nota de seguridad**: nunca hardcodees credenciales en archivos del repo. Usa AWS SSO si tu organización lo soporta, o roles asumibles.

### 2.3 Validar el código Terraform localmente

Antes de tocar AWS, valida que el código Terraform parsea sin errores:

```bash
cd Infra-AgentCore
./scripts/tf-check.sh
```

Salida esperada al final:
```
==> OK
```

Si hay errores, **detente aquí** y resuélvelos antes de continuar. El script:
- Ejecuta `tofu fmt -check -recursive` (estilo canónico)
- Ejecuta `tofu init -backend=false && tofu validate` en cada composition y foundation module

---

## 3. Bootstrap inicial de una cuenta AWS

> ⚠️ Este paso se hace **una sola vez por cuenta AWS**. Crea recursos compartidos (KMS, S3, IAM roles base, gateways por defecto). NO lo ejecutes si la cuenta ya fue inicializada.

### 3.1 Verificar que la cuenta está virgen

```bash
# Buscar recursos foundation existentes
aws kms list-aliases --query "Aliases[?contains(AliasName, 'agentcore')]"
aws s3 ls | grep agentcore
aws iam list-roles --query "Roles[?contains(RoleName, 'agentcore')]"
```

Si los 3 comandos retornan vacío, la cuenta está lista para bootstrap.

### 3.2 Configurar el backend de state

Foundation maneja state propio aislado del resto. Necesitas un bucket S3 con KMS para guardar el state.

Opción A: usar GitLab managed state (recomendado si tu organización lo soporta).

Opción B: bucket S3 manual:

```bash
# Crear bucket de state UNA SOLA VEZ por cuenta
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENV=dev

aws s3api create-bucket \
  --bucket "tfstate-agentcore-${ENV}-${ACCOUNT_ID}" \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket "tfstate-agentcore-${ENV}-${ACCOUNT_ID}" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "tfstate-agentcore-${ENV}-${ACCOUNT_ID}" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### 3.3 Aplicar `foundation/bootstrap`

Crea KMS keys, S3 buckets, IAM roles base.

```bash
cd Infra-AgentCore/foundation/bootstrap

# Configurar backend de state (ajusta según paso 3.2)
cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket = "tfstate-agentcore-dev-${ACCOUNT_ID}"
    key    = "foundation/bootstrap.tfstate"
    region = "us-east-1"
  }
}
EOF

# Crear archivo de variables
cat > terraform.tfvars <<EOF
environment            = "dev"
region                 = "us-east-1"
deployer_principals    = ["arn:aws:iam::${ACCOUNT_ID}:role/gitlab-deployer-dev"]
EOF

# Aplicar
tofu init
tofu plan -out=plan.tfplan
# Revisa el plan: deberían crearse ~12 recursos (2 KMS, 3 buckets + lifecycle, 1 IAM role, etc.)

tofu apply plan.tfplan
```

Captura los outputs para usar en el siguiente paso:

```bash
tofu output -json > /tmp/foundation-outputs.json
cat /tmp/foundation-outputs.json | jq
# Vas a ver: kms_artifacts_arn, kms_secrets_arn, s3_buckets, runtime_role_arn
```

### 3.4 Aplicar `foundation/default-gateways`

Crea los 3 gateways AgentCore por defecto del ambiente.

> Antes de aplicar, necesitas las URLs de discovery del IdP corporativo para 3LO y 2LO. Coordina con el equipo de IAM corporativo.

```bash
cd ../default-gateways

cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket = "tfstate-agentcore-dev-${ACCOUNT_ID}"
    key    = "foundation/default-gateways.tfstate"
    region = "us-east-1"
  }
}
EOF

cat > terraform.tfvars <<EOF
environment              = "dev"
region                   = "us-east-1"
oauth_3lo_discovery_url  = "https://idp.tuempresa.com/.well-known/openid-configuration"
oauth_2lo_discovery_url  = "https://idp.tuempresa.com/.well-known/openid-configuration"
allowed_audience_3lo     = ["agentcore-dev"]
allowed_audience_2lo     = ["agentcore-dev-m2m"]
EOF

tofu init
tofu plan -out=plan.tfplan
tofu apply plan.tfplan

# Captura outputs
tofu output -json > /tmp/gateways-outputs.json
```

### 3.5 Aplicar `foundation/vpc-endpoints` (opcional pero recomendado)

Si tu cuenta tiene una VPC dedicada y quieres tráfico privado a Bedrock/S3/ECR:

```bash
cd ../vpc-endpoints

# Configurar backend
cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket = "tfstate-agentcore-dev-${ACCOUNT_ID}"
    key    = "foundation/vpc-endpoints.tfstate"
    region = "us-east-1"
  }
}
EOF

cat > terraform.tfvars <<EOF
environment        = "dev"
region             = "us-east-1"
vpc_id             = "vpc-XXXXXXXX"
subnet_ids         = ["subnet-AAA", "subnet-BBB"]
security_group_ids = ["sg-XXXXXXXX"]
EOF

tofu init
tofu plan -out=plan.tfplan
tofu apply plan.tfplan
```

### 3.6 Validar bootstrap completo

```bash
# Las KMS keys existen
aws kms list-aliases --query "Aliases[?contains(AliasName, 'agentcore')]"

# Los buckets existen
aws s3 ls | grep agentcore

# Los gateways existen
aws bedrock-agentcore-control list-gateways --region us-east-1

# El role base existe
aws iam get-role --role-name agentcore-dev-runtime-execution
```

Si los 4 comandos retornan datos consistentes, foundation está lista.

---

## 4. Configuración del CI/CD

### 4.1 Variables CI/CD requeridas

En GitLab, configura las siguientes variables a nivel de grupo o proyecto. Usa scope `environment: dev` para dev, `qa` para qa, `prd` para prd.

| Variable | Tipo | Scope | Descripción |
|----------|------|-------|-------------|
| `AWS_ROLE_ARN_DEV` | Variable | dev | ARN del role que GitLab asume con OIDC |
| `AWS_ROLE_ARN_QA` | Variable | qa | Idem para qa |
| `AWS_ROLE_ARN_PRD` | Variable | prd | Idem para prd |
| `S3_ARTIFACTS_BUCKET` | Variable | * | Nombre del bucket creado en bootstrap |
| `ECR_REGISTRY_PATTERN` | Variable | * | Patrón ECR (`${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com`) |
| `IMAGE_BASE` | Variable | * | Imagen del runner que ejecuta los componentes |
| `ORG_RUNNER_IMAGE` | Variable | * | Imagen base del runner GitLab |
| `INFRA_REF` | Variable | * | Tag de `Infra-AgentCore` a usar (ej: `v1.2.0`) |

Lista completa en [`CI_VARIABLES.md`](../CI_VARIABLES.md).

### 4.2 Configurar OIDC entre GitLab y AWS

Para que el pipeline de GitLab asuma roles AWS sin credenciales hardcodeadas:

1. En AWS, crea un OIDC identity provider apuntando al servidor GitLab:

```bash
aws iam create-open-id-connect-provider \
  --url "https://gitlab.tuempresa.com" \
  --client-id-list "https://gitlab.tuempresa.com" \
  --thumbprint-list "<thumbprint del cert>"
```

2. Crea un role con trust policy permitiendo el assume desde GitLab:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT:oidc-provider/gitlab.tuempresa.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "gitlab.tuempresa.com:aud": "https://gitlab.tuempresa.com"
      },
      "StringLike": {
        "gitlab.tuempresa.com:sub": "project_path:tu-grupo/AgentPlatform:ref_type:branch:ref:dev"
      }
    }
  }]
}
```

3. Adjunta políticas al role: permisos para Bedrock, ECR, S3 (artefactos), Secrets Manager, KMS (decrypt para artefactos).

### 4.3 Validar el harness CI

En `Infra-AgentCore`, el `.gitlab-ci.yml` valida HCL en cada MR:

```yaml
# Ya configurado en .gitlab-ci.yml
stages:
  - check

tf-fmt-check:
  script:
    - terraform fmt -check -recursive .

tf-validate:
  script:
    - bash scripts/tf-check.sh
```

Crea un MR de prueba (cambio trivial) y verifica que ambos jobs pasan en verde antes de continuar.

---

## 5. Despliegue del primer agente

> Hito crítico de validación. Hasta que un agente real funcione end-to-end, la plataforma es teoría.

### 5.1 Crear el manifest del agente

En `AgentPlatform/agents/`, copia el template:

```bash
cd AgentPlatform
cp -r agents/_template agents/platform-test/hello-agent
cd agents/platform-test/hello-agent
```

Edita `manifest.yaml` con valores mínimos:

```yaml
apiVersion: agentcore.io/v1
kind: Agent
metadata:
  name: hello-agent
  capability: platform-test
  owner: platform-team@tuempresa.com
spec:
  composition: agent-base    # el más simple, sin memory ni KB ni tools
  runtime:
    entrypoint: agent.py
    env:
      LOG_LEVEL: INFO
  models:
    - alias: PRIMARY
      provider: bedrock
      model_id: anthropic.claude-3-5-sonnet-20241022-v2:0
      region: us-east-1
  features:
    enable_observability: true
  tags:
    - platform-test
    - tutorial
```

### 5.2 Implementar el código mínimo del agente

`src/agent.py`:

```python
import os
from fastapi import FastAPI

app = FastAPI()

PRIMARY_MODEL_ID = os.environ.get("PRIMARY_MODEL_ID")

@app.get("/ping")
async def ping():
    return {"status": "ok", "model": PRIMARY_MODEL_ID}

@app.post("/invocations")
async def invoke(payload: dict):
    # Lógica mínima: echo del prompt con info del modelo
    prompt = payload.get("prompt", "")
    return {
        "response": f"Echo: {prompt}",
        "model": PRIMARY_MODEL_ID,
    }
```

`src/requirements.txt`:

```
fastapi==0.115.0
uvicorn==0.30.0
boto3==1.35.0
```

`src/Dockerfile` (opcional, hay default):

```dockerfile
FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY agent.py ./
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 5.3 Pushear a `dev` y observar el pipeline

```bash
git checkout -b dev    # si no existe
git add agents/platform-test/hello-agent/
git commit -m "feat: hello-agent for platform validation"
git push origin dev
```

Ve al pipeline en GitLab. Deberías ver los stages:

```
.pre              telemetry-start
validate          validate-manifest, validate-structure
package           package-artifact
build             build-image
scan              scan-image
secrets           (sin secrets en este caso, skipped)
publish-prompts   (sin prompts en este caso, skipped)
render            apply-policy, render-tfvars
deploy            trigger-iac → dispara pipeline downstream en agentcore-dev
smoke             smoke-test
.post             telemetry-end
```

Cada stage debería tomar entre 30s y 5 minutos. Total esperado: 10-20 minutos para el primer despliegue (build de imagen es lo más lento).

### 5.4 Si algo falla, ver el log del job

GitLab → tu MR → Pipelines → click en el job rojo → tab "Job log".

Errores frecuentes en este punto se cubren en [§7 Troubleshooting](#7-troubleshooting-común).

---

## 6. Verificación end-to-end

### 6.1 Confirmar que el runtime existe en AWS

```bash
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1
```

Deberías ver tu agente con nombre `hello-agent-dev` y status `READY`.

### 6.2 Probar `/ping`

Captura el ARN del runtime:

```bash
RUNTIME_ARN=$(aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='hello-agent-dev'].agentRuntimeArn" \
  --output text)
echo $RUNTIME_ARN
```

Invoca el endpoint:

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --payload '{"path": "/ping"}' \
  --region us-east-1 \
  /tmp/response.json

cat /tmp/response.json
# Esperado: {"status": "ok", "model": "anthropic.claude-3-5-sonnet-20241022-v2:0"}
```

### 6.3 Probar `/invocations`

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --payload '{"path": "/invocations", "body": {"prompt": "hola"}}' \
  --region us-east-1 \
  /tmp/response.json

cat /tmp/response.json
# Esperado: {"response": "Echo: hola", ...}
```

### 6.4 Verificar logs en CloudWatch

```bash
aws logs tail /aws/bedrock-agentcore/hello-agent-dev --follow
```

Deberías ver requests entrantes y respuestas. Si los logs no aparecen en 5 minutos, ver §7.4.

### 6.5 Verificar el dashboard de observability

Si habilitaste `enable_observability: true`:

```bash
# Listar dashboards
aws cloudwatch list-dashboards --region us-east-1 \
  --query "DashboardEntries[?contains(DashboardName, 'hello-agent-dev')]"

# Abrir en consola: link directo
echo "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=agentcore-dev-hello-agent-dev"
```

---

## 7. Troubleshooting común

### 7.1 `validate-manifest` falla con "schema validation failed"

**Causa**: el manifest no cumple el JSON-schema en `Componentes-AgentCore/config_files/validate_manifest/manifest.schema.json`.

**Solución**: el log del job muestra el path del campo problemático. Compara contra `MANIFEST_REFERENCE.md` y `agents/_template/manifest.yaml`.

Validación local rápida:

```bash
cd Componentes-AgentCore
python -m src.validate_manifest.validate \
  --manifest ../AgentPlatform/agents/platform-test/hello-agent/manifest.yaml
```

### 7.2 `build-image` falla con "platform mismatch"

**Causa**: el Dockerfile o el runner no soportan ARM64 (AgentCore exige ARM64).

**Solución**:
- Confirma que la imagen base del Dockerfile es multi-arch (las imágenes oficiales de AWS Lambda Python lo son).
- Confirma que el runner GitLab tiene `docker buildx` y soporte de QEMU para multi-arch.
- En el log busca la línea `--platform linux/arm64`. Si dice `linux/amd64`, hay un override del builder.

### 7.3 `scan-image` falla con CVEs HIGH+

**Causa**: la imagen tiene vulnerabilidades de severidad HIGH o CRITICAL.

**Solución**:
- Ver el reporte completo en el artifact `scan_report.json` del job.
- Actualizar versiones en `requirements.txt`.
- Si es un falso positivo o no es explotable, agregar al allowlist en `Componentes-AgentCore/config_files/scan_image/cve_allowlist.yml` con justificación documentada.

### 7.4 `terraform apply` (downstream) falla con "Error creating agent runtime"

**Causa común 1**: el role del runtime no tiene permisos para hacer pull de ECR.

**Solución**: verificar que `agentcore-dev-runtime-execution` tiene la policy de ECR adjunta. Si no, ver §3.3 del bootstrap.

**Causa común 2**: la imagen no está en ECR todavía.

**Solución**: confirmar que `build-image` terminó exitoso y la imagen está en `aws ecr describe-images --repository-name agentcore-agents-platform-test-hello-agent`.

**Causa común 3**: schema del provider AWS cambió.

**Solución**: actualizar el código en `Infra-AgentCore/modules/runtime/main.tf` según el schema actual del provider. Ver el output de `tofu providers schema -json | jq '.provider_schemas[] | .resource_schemas.aws_bedrockagentcore_agent_runtime'`.

### 7.5 `smoke-test` falla con timeout

**Causa**: el runtime tarda en bootear (cold start) más que el timeout del smoke test.

**Solución**:
- Verifica que la imagen es lo más liviana posible (eliminar dependencias innecesarias).
- Ajusta el timeout en `Componentes-AgentCore/templates/smoke_test/template.yml` si es genuinamente lento.
- Investiga logs del runtime para ver si el container está crasheando en el startup.

### 7.6 Runtime queda en estado `CREATE_FAILED`

```bash
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id <ID> \
  --region us-east-1 \
  --query "failureReasons"
```

Causas comunes:
- IAM role mal configurado (falta `bedrock-agentcore.amazonaws.com` en trust policy)
- KMS key sin permiso para el role
- VPC sin endpoint a `bedrock-agentcore` (si runtime está en modo VPC)

### 7.7 ENI orphans tras `terraform destroy` (issue #45099)

**Síntoma**: `terraform destroy` exitoso pero quedan ENIs huérfanas asociadas a la subnet.

**Solución temporal**: borrar manualmente:

```bash
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*agentcore*" \
  --query "NetworkInterfaces[?Status=='available'].NetworkInterfaceId" \
  --output text | xargs -I {} aws ec2 delete-network-interface --network-interface-id {}
```

Solución permanente: implementar item 1.4 de `01_IMPROVEMENTS_AND_FUTURE_WORK.md`.

---

## 8. Operación día a día

### 8.1 Dashboard de salud de la plataforma

Cosas que el equipo debe revisar a diario (idealmente automatizado con alertas):

| Métrica | Umbral de alerta | Acción si se cruza |
|---------|------------------|---------------------|
| % runtimes en estado `READY` | < 95% | Investigar runtimes en `CREATE_FAILED` o `UPDATE_FAILED` |
| Error rate p95 por composition | > 1% | Revisar logs del runtime con más errores |
| Latencia p99 por composition | Según SLO definido (ver 10.1) | Profiling y optimización |
| Costo diario Bedrock | > 120% del baseline | Identificar workload con consumo anómalo |
| Quota Bedrock vs uso | > 70% | Solicitar aumento de quota a AWS |
| Drift detectado | > 0 | Investigar y reconciliar (ver 8.4) |
| ECR storage | > 80% | Lifecycle policy de imágenes viejas |
| Gateway request rate | > 80% del límite | Considerar shard nuevo |

### 8.2 Drift detection semanal

Cron que ejecuta `terraform plan -refresh=true -detailed-exitcode` por composition. Si exit code != 0 ni 2, hay drift.

```bash
# Implementación manual mientras 1.9 no esté
for env in dev qa prd; do
  for comp_dir in iac/AgentCore/agentcore-${env}/states/*/; do
    cd $comp_dir
    if ! terraform plan -refresh=true -detailed-exitcode > /dev/null; then
      echo "DRIFT en $comp_dir"
    fi
  done
done
```

Si hay drift, posibles causas:
- Alguien tocó por consola AWS (mal practice — corregir y educar)
- AWS cambió un default (raro pero pasa con servicios nuevos)
- El provider Terraform cambió comportamiento al hacer upgrade

Acción: investigar causa, decidir si reconciliar (`terraform apply`) o ajustar código.

### 8.3 Rotación de imágenes ECR

Por defecto las imágenes se acumulan. Configura lifecycle policy:

```bash
aws ecr put-lifecycle-policy \
  --repository-name agentcore-agents-platform-test-hello-agent \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "description": "Keep last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": { "type": "expire" }
    }]
  }'
```

Idealmente esto se aplica desde Terraform en el módulo del workload.

### 8.4 Reconciliación de drift

Si detectas drift y decides reconciliar:

1. Revisa el `terraform plan` con detalle: ¿qué cambió y por qué?
2. Si el cambio es legítimo (alguien fixeó algo a mano por urgencia), copia el cambio al código y haz commit.
3. Si el cambio NO es legítimo (alguien tocó sin autorización), reverte con `terraform apply` y educa al responsable.
4. Documenta en un ticket interno para postmortem si fue un cambio crítico.

### 8.5 Upgrade del provider AWS

AgentCore evoluciona rápido. Plan trimestral:

1. Revisar changelog del provider entre la versión actual y la última: https://github.com/hashicorp/terraform-provider-aws/releases
2. Buscar breaking changes en recursos `aws_bedrockagentcore_*`.
3. En una rama, actualizar `versions.tf` (subir `~> 6.53.0` a `~> 6.5X.0`).
4. Ejecutar `tofu init -upgrade` y `./scripts/tf-check.sh`.
5. Si pasa, hacer MR. Si falla, ajustar código módulo por módulo siguiendo errores del validate.
6. Probar en sandbox antes de mergear a `main`.

### 8.6 Secret rotation

Para los secrets en Secrets Manager (Azure API keys, OAuth client secrets):

- Hoy es manual. Plan: implementar item 7.10 (rotación automática).
- Mientras tanto: cron que avisa al equipo cuando un secret pasa los 90 días sin rotar.

```bash
# Listar secrets cerca de los 90 días
aws secretsmanager list-secrets \
  --query "SecretList[?LastChangedDate < '$(date -v-90d -u +%Y-%m-%dT%H:%M:%SZ)'].Name"
```

---

## 9. Onboarding de nuevos equipos consumidores

Cuando un equipo de capability te pide subir un agente:

### 9.1 Reunión inicial (30 min)

Cubre:
- ¿Qué tipo de workload es? (chatbot, automatización, MCP server, herramienta)
- ¿Qué modelos necesita? ¿Bedrock, Azure, ambos?
- ¿Necesita Knowledge Base? ¿Qué fuentes?
- ¿Necesita tools externos? ¿Hay APIs preexistentes?
- ¿Qué clasificación de datos toca? (PII, transaccional, público)
- ¿Quién es el owner técnico y de negocio?

Output: composition recomendada (`agent-chatbot`, `agent-with-tools`, etc.) y un manifest skeleton.

### 9.2 Checklist para el equipo consumidor

Envíales por mail o ticket:

- [ ] Leer `AgentPlatform/README.md`
- [ ] Leer `MANIFEST_REFERENCE.md` (sección de su composition)
- [ ] Copiar `agents/_template/` a su path (`agents/<su-capability>/<su-nombre>/`)
- [ ] Editar `manifest.yaml` con sus valores
- [ ] Implementar `src/agent.py` con `/ping` y `/invocations`
- [ ] Probar localmente con `pytest tests/`
- [ ] Push a `dev`
- [ ] Validar smoke test exitoso
- [ ] Demo del agente al equipo de plataforma
- [ ] MR `dev` → `qa` con approval del equipo
- [ ] Después de validación en QA: tag `vX.Y.Z` y merge a `main` para PRD

### 9.3 Soporte durante la primera semana

Reuniones cortas (15 min) cada 2 días para resolver bloqueos:
- Errores del pipeline
- Dudas sobre features del manifest
- Pregunta sobre integración con sistemas externos

Después de la primera semana, el equipo debería ser autónomo. Si no lo es, hay un problema de documentación o complejidad que debes capturar como mejora.

### 9.4 Decision tree para elegir composition

```
¿El workload expone API a otros agentes?
├── SÍ → mcp-server
└── NO
    │
    ├── ¿Es una herramienta aislada (no LLM)?
    │   └── SÍ → tool-lambda
    │
    └── ¿Necesita LLM?
        ├── ¿Necesita Knowledge Base?
        │   └── SÍ → agent-with-kb
        │
        ├── ¿Necesita tools externos?
        │   └── SÍ → agent-with-tools
        │
        ├── ¿Solo conversación?
        │   └── SÍ → agent-chatbot
        │
        └── ¿Sin memory ni KB ni tools?
            └── agent-base
```

---

## 10. Procedimientos de emergencia

### 10.1 Agente caído en PRD

1. Página al on-call vía PagerDuty / Slack.
2. On-call abre runbook específico (ver `Infra-AgentCore/RUNBOOK_*.md`).
3. Mitigación inmediata:
   - Si la versión actual está rota: rollback a versión previa.
   - Si todo el runtime está caído: redeploy desde último commit verde.
4. Comunicación: actualizar status page interno cada 30 min.
5. Postmortem dentro de 48h hábiles.

### 10.2 Secret comprometido

1. Rotar el secret inmediatamente en Secrets Manager.
2. Identificar todos los workloads que lo usan (grep en manifests).
3. Forzar redeploy de cada workload afectado.
4. Auditar logs del IdP corporativo: ¿hubo accesos sospechosos con ese secret?
5. Notificar al equipo de seguridad corporativa.
6. Postmortem con root cause analysis.

### 10.3 Drift masivo (>10 recursos)

1. **NO ejecutar `terraform apply` automáticamente**.
2. Investigar quién hizo cambios (CloudTrail).
3. Si fue legítimo: capturar cambios en código y commit.
4. Si fue accidental o malicioso: comunicar y ejecutar apply para reconciliar.
5. Revisar permisos: ¿alguien tiene acceso console que no debería tener?

### 10.4 Destroy accidental en PRD

Ver `RUNBOOK_DESTROY_PRD.md` completo. Resumen:

1. **Si el destroy aún no terminó**: cancelar el job de GitLab inmediatamente.
2. **Si terminó**: revisar el state file. Algunos recursos (KMS keys con `deletion_window_in_days`) pueden recuperarse en los 30 días siguientes.
3. **Para recursos perdidos**: redeploy desde el último commit verde + restore de datos desde backups (S3 versioning, KB exports).
4. **Postmortem inmediato**: ¿cómo llegó el destroy a PRD? ¿faltó approval? ¿deny policy no se aplicó?
5. Reforzar las 4 capas de protección documentadas en `MANIFEST_REFERENCE.md` §"protección PRD".

---

## Próximos pasos

Después de completar este tutorial:

1. Ejecuta el flujo end-to-end con 2-3 agentes adicionales de complejidad creciente (con KB, con tools, MCP server).
2. Documenta los problemas que encuentres en `tasks/lessons.md` para feedback continuo.
3. Identifica qué items de `01_IMPROVEMENTS_AND_FUTURE_WORK.md` se vuelven críticos según tu experiencia operando.
4. Comparte aprendizajes en sesiones internas del equipo de plataforma.

## Referencias rápidas

| Necesito... | Voy a... |
|-------------|----------|
| Entender qué hace cada repo | [`docs/resumen.md`](resumen.md) |
| Saber qué campo va en el manifest | [`MANIFEST_REFERENCE.md`](../MANIFEST_REFERENCE.md) |
| Validar HCL local | `cd Infra-AgentCore && ./scripts/tf-check.sh` |
| Ver el plan de fases | [`02_PHASED_IMPLEMENTATION_PLAN.md`](02_PHASED_IMPLEMENTATION_PLAN.md) |
| Saber qué quotas pedir a AWS | [`07_QUOTAS.md`](07_QUOTAS.md) |
| Mejoras pendientes y trabajo futuro | [`01_IMPROVEMENTS_AND_FUTURE_WORK.md`](01_IMPROVEMENTS_AND_FUTURE_WORK.md) |
| Diagrama de flujos | [`05_FLOWS_AND_DIAGRAMS.md`](05_FLOWS_AND_DIAGRAMS.md) |
| Variables CI/CD | [`../CI_VARIABLES.md`](../CI_VARIABLES.md) |
| Multi-cuenta setup | [`../MULTI_ACCOUNT.md`](../MULTI_ACCOUNT.md) |
| Runbook de destroy en PRD | [`../RUNBOOK_DESTROY_PRD.md`](../RUNBOOK_DESTROY_PRD.md) |
