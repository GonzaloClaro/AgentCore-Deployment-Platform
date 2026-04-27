# Tutorial — Adoptar fase 0 desde cero

> Guía paso a paso para un equipo que recibe esta carpeta y quiere poner la plataforma en marcha. Asume cuenta AWS sandbox + GitLab (puede ser self-hosted o gitlab.com).

## Tabla de contenidos

1. [Prerequisitos](#1-prerequisitos)
2. [Setup local](#2-setup-local)
3. [Bootstrap de la cuenta AWS](#3-bootstrap-de-la-cuenta-aws)
4. [Subir fase 0 a GitLab](#4-subir-fase-0-a-gitlab)
5. [Configurar OIDC + variables CI/CD](#5-configurar-oidc--variables-cicd)
6. [Desplegar el primer agente](#6-desplegar-el-primer-agente)
7. [Verificación end-to-end](#7-verificación-end-to-end)
8. [Troubleshooting común](#8-troubleshooting-común)

---

## 1. Prerequisitos

### Accesos
- Cuenta AWS con permisos Admin (sandbox/dev personal)
- Cuenta GitLab con permisos para crear groups y proyectos
- Identidad verificada en GitLab (para usar shared runners gratis)

### Tooling local

```bash
# macOS con Homebrew
brew install opentofu              # o terraform
brew install awscli
brew install glab                  # GitLab CLI
brew install jq yq

# Verificación
tofu version           # >= 1.9
aws --version          # >= 2.x
glab --version
```

### Conocimiento previo
- Terraform intermedio
- AWS IAM/KMS/S3 básico
- GitLab CI/CD básico
- Python 3.12+

---

## 2. Setup local

### 2.1 Clonar este directorio

Esta carpeta `fase0/` es **autocontenida**. Clonala (o copiala) a tu máquina:

```bash
git clone <repo-con-fase0> ~/agentcore-fase0
cd ~/agentcore-fase0/fase0
```

### 2.2 Configurar AWS CLI

```bash
aws configure --profile fase0-dev
# AWS Access Key ID:     <tu access key>
# AWS Secret Access Key: <tu secret>
# Default region:        us-east-1
# Default output:        json

export AWS_PROFILE=fase0-dev
aws sts get-caller-identity
```

### 2.3 Validar Terraform localmente

```bash
cd Infra-AgentCore
./scripts/tf-check.sh
```

Salida esperada al final: `==> OK`. Si falla, detente y revisa antes de continuar.

---

## 3. Bootstrap de la cuenta AWS

> ⚠️ Este paso se hace **una vez por cuenta**. Crea KMS keys, S3 buckets, IAM role base.

### 3.1 Backend de state

Crear bucket para Terraform state:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws s3api create-bucket \
  --bucket "tfstate-fase0-${ACCOUNT_ID}" \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket "tfstate-fase0-${ACCOUNT_ID}" \
  --versioning-configuration Status=Enabled
```

### 3.2 Aplicar `foundation/bootstrap`

```bash
cd Infra-AgentCore/foundation/bootstrap

cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket = "tfstate-fase0-${ACCOUNT_ID}"
    key    = "foundation/bootstrap.tfstate"
    region = "us-east-1"
  }
}
EOF

cat > terraform.tfvars <<EOF
environment         = "dev"
region              = "us-east-1"
deployer_principals = []
EOF

tofu init
tofu plan -out=plan.tfplan
tofu apply plan.tfplan
```

### 3.3 Capturar outputs

```bash
tofu output -json > /tmp/foundation-outputs.json
cat /tmp/foundation-outputs.json | jq
```

Necesitarás:
- `kms_artifacts_arn`
- `runtime_role_arn`
- `s3_buckets` → `agents` (el bucket donde van los zip de agentes)

### 3.4 (Opcional) Aplicar foundations de gateways y VPC endpoints

Si tu agente va a usar gateways o tráfico privado:

```bash
cd ../default-gateways
# Edita terraform.tfvars con URLs OIDC de tu IdP corporativo
tofu init && tofu apply

cd ../vpc-endpoints
# Edita terraform.tfvars con vpc_id y subnet_ids
tofu init && tofu apply
```

Para fase 0 mínima, solo `bootstrap` es necesario.

---

## 4. Subir fase 0 a GitLab

### 4.1 Crear el group top-level

Como gitlab.com Free no permite crear groups top-level vía API, hazlo desde la UI:

1. https://gitlab.com/groups/new
2. **Group name**: `mi-agentcore-fase0` (o el nombre que prefieras)
3. **Visibility**: Public o Private según preferencia
4. Click **Create group**

### 4.2 Crear los 7 proyectos vía glab

```bash
glab auth login   # OAuth flow con browser
GROUP=mi-agentcore-fase0  # ajustar al nombre que elegiste

# Helper para parent_id de subgroups
ROOT_ID=$(glab api "groups/$GROUP" | jq -r '.id')

# Subgroups
COMP_ID=$(glab api groups -X POST -f name=Componentes -f path=Componentes \
  -f visibility=public -f parent_id=$ROOT_ID | jq -r '.id')
COMPOSE_ID=$(glab api groups -X POST -f name=Compose -f path=Compose \
  -f visibility=public -f parent_id=$COMP_ID | jq -r '.id')
IAC_ID=$(glab api groups -X POST -f name=iac -f path=iac \
  -f visibility=public -f parent_id=$ROOT_ID | jq -r '.id')
AGCORE_ID=$(glab api groups -X POST -f name=AgentCore -f path=AgentCore \
  -f visibility=public -f parent_id=$IAC_ID | jq -r '.id')

# Proyectos
for spec in "AgentPlatform:$ROOT_ID" "agentcore:$COMP_ID" "agentcore:$COMPOSE_ID" \
            "infra-agentcore:$AGCORE_ID" "agentcore-dev:$AGCORE_ID" \
            "agentcore-qa:$AGCORE_ID" "agentcore-prd:$AGCORE_ID"; do
  IFS=':' read name nsid <<< "$spec"
  glab api projects -X POST -f name=$name -f path=$name \
    -f namespace_id=$nsid -f visibility=public -f initialize_with_readme=false
done
```

### 4.3 Pushear cada subdirectorio

Desde la raíz de fase0/:

```bash
cd /path/to/fase0

# Por cada subdir, init + remote + push
for spec in \
  "AgentPlatform:AgentPlatform" \
  "Componentes-AgentCore:Componentes/agentcore" \
  "Compose-AgentCore:Componentes/Compose/agentcore" \
  "Infra-AgentCore:iac/AgentCore/infra-agentcore" \
  "iac/AgentCore/agentcore-dev:iac/AgentCore/agentcore-dev" \
  "iac/AgentCore/agentcore-qa:iac/AgentCore/agentcore-qa" \
  "iac/AgentCore/agentcore-prd:iac/AgentCore/agentcore-prd"; do
  IFS=':' read local_path gitlab_path <<< "$spec"
  cd "$local_path"
  git init -q
  git add .
  git -c user.email="$(git config user.email)" -c user.name="$(git config user.name)" \
      commit -q -m "initial commit"
  git remote add origin "https://gitlab.com/$GROUP/$gitlab_path.git"
  git push -u origin main
  cd -
done
```

### 4.4 Ajustar cross-references en los `.gitlab-ci.yml`

Las referencias entre proyectos están hardcoded a `Componentes/Compose/agentcore` (sin namespace). Hay que prefijar con tu group:

```bash
# En cada repo que ya pusheaste, hacer find/replace
find . -name "*.yml" -exec sed -i '' \
  -e "s|project: Componentes/agentcore|project: $GROUP/Componentes/agentcore|g" \
  -e "s|project: Componentes/Compose/agentcore|project: $GROUP/Componentes/Compose/agentcore|g" \
  -e "s|/iac/AgentCore/infra-agentcore.git|/$GROUP/iac/AgentCore/infra-agentcore.git|g" \
  -e "s|\$CI_SERVER_FQDN/Componentes/agentcore|\$CI_SERVER_FQDN/$GROUP/Componentes/agentcore|g" \
  {} \;

# Commit + push del fix por cada repo afectado
```

---

## 5. Configurar OIDC + variables CI/CD

Ver detalle en [`CI_VARIABLES.md`](CI_VARIABLES.md). Resumen:

### 5.1 OIDC trust en AWS

```bash
THUMBPRINT=$(echo | openssl s_client -servername gitlab.com -showcerts \
  -connect gitlab.com:443 2>/dev/null | openssl x509 -fingerprint -noout -sha1 \
  | sed 's/.*=//' | tr -d ':' | tr 'A-Z' 'a-z')

aws iam create-open-id-connect-provider \
  --url "https://gitlab.com" \
  --client-id-list "https://gitlab.com" \
  --thumbprint-list "$THUMBPRINT"

cat > /tmp/trust.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/gitlab.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "gitlab.com:aud": "https://gitlab.com" },
      "StringLike": { "gitlab.com:sub": "project_path:${GROUP}/*" }
    }
  }]
}
EOF

aws iam create-role --role-name gitlab-deployer-dev \
  --assume-role-policy-document file:///tmp/trust.json

aws iam attach-role-policy --role-name gitlab-deployer-dev \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

### 5.2 Configurar 4 variables en el group

En GitLab: `<group>/settings/ci_cd` → Variables.

| Key | Value | Scope | Masked |
|-----|-------|-------|--------|
| `AWS_ROLE_ARN_DEV` | `arn:aws:iam::<ACCOUNT_ID>:role/gitlab-deployer-dev` | `*` | ✅ |
| `AWS_ACCOUNT_ID_DEV` | `<ACCOUNT_ID>` | `*` | ✅ |
| `AWS_REGION` | `us-east-1` | `*` | ❌ |
| `ORG_RUNNER_IMAGE` | `python:3.12-slim` | `*` | ❌ |

### 5.3 Verificar identidad GitLab (para shared runners)

https://gitlab.com/-/profile/account → "Account verification" → seguir flujo (teléfono o tarjeta sin cargo).

---

## 6. Desplegar el primer agente

### 6.1 Crear el manifest

En el repo `AgentPlatform`:

```bash
cd AgentPlatform
cp -r agents/_template agents/platform-test/hello-agent
cd agents/platform-test/hello-agent
```

Editá `manifest.yaml`:

```yaml
apiVersion: v1
kind: Agent
metadata:
  name: hello-agent
  capability: platform-test
  owner: tu-email@example.com
spec:
  composition: agent-base-zip
  runtime:
    entrypoint: main.py
  models:
    - alias: PRIMARY
      provider: bedrock
      bedrock:
        model_id: amazon.nova-micro-v1:0
        region: us-east-1
  features:
    enable_observability: true
```

### 6.2 (Opcional) Editar `src/main.py`

El template ya viene con un mock funcional. Para un agente real, llamá Bedrock:

```python
import boto3, os, json
from http.server import BaseHTTPRequestHandler, HTTPServer

bedrock = boto3.client("bedrock-runtime", region_name=os.environ["PRIMARY_MODEL_REGION"])

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ping":
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
    def do_POST(self):
        if self.path != "/invocations":
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))
        prompt = payload.get("prompt", "")
        resp = bedrock.converse(
            modelId=os.environ["PRIMARY_MODEL_ID"],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )
        self.send_response(200); self.end_headers()
        self.wfile.write(json.dumps({"response": resp["output"]["message"]["content"][0]["text"]}).encode())

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
```

### 6.3 Push y observar el pipeline

```bash
git add agents/platform-test/hello-agent/
git commit -m "feat: hello-agent"
git push
```

En GitLab → Pipelines, deberías ver corriendo:

```
.pre              telemetry-start
validate          validate-manifest, validate-structure
package           package-artifact
secrets           (skipped si no hay azure)
publish-prompts   (skipped si no hay prompts)
render            render-tfvars
deploy            trigger-iac → dispara pipeline en agentcore-dev
smoke             smoke-test
.post             telemetry-end
```

Total esperado: ~5-10 minutos para el primer despliegue.

---

## 7. Verificación end-to-end

### 7.1 Verificar que el runtime existe en AWS

```bash
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1
```

Deberías ver `hello_agent` (snake_case) con status `READY`.

### 7.2 Probar `/ping`

```bash
RUNTIME_ARN=$(aws bedrock-agentcore-control list-agent-runtimes \
  --region us-east-1 \
  --query "agentRuntimes[?agentRuntimeName=='hello_agent'].agentRuntimeArn" \
  --output text)

aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --payload '{"path":"/ping"}' \
  --region us-east-1 \
  /tmp/response.json

cat /tmp/response.json
```

### 7.3 Logs en CloudWatch

```bash
aws logs tail /aws/bedrock-agentcore/hello_agent --follow --region us-east-1
```

---

## 8. Troubleshooting común

### `validate-manifest` falla con "schema validation failed"

El manifest no cumple el JSON-schema. Comparalo contra `agents/_template/manifest.yaml` y `MANIFEST_REFERENCE.md`. Validación local rápida:

```bash
cd Componentes-AgentCore
MANIFEST_PATH=../AgentPlatform/agents/<capability>/<name>/manifest.yaml \
  python -m src.validate_manifest.validate
```

### `validate-structure` falla con "composition no soportada"

En fase 0 solo `agent-base-zip` y `agent-with-kb-zip` son válidas. Las demás composiciones no existen.

### `terraform apply` falla con "maxAgents limit exceeded"

Cuotas de AgentCore están en 0 por ser cuenta nueva. Abre AWS Support y pedí increase de "Total Agents per Account" a 5.

### Runtime queda en `CREATE_FAILED`

```bash
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id <ID> --region us-east-1 \
  --query "failureReasons"
```

Causas comunes:
- IAM trust policy mal armada
- Role sin permisos para s3:GetObject sobre el bucket de artifacts
- KMS key sin grant para el role

### Smoke test falla con timeout

El runtime tarda en bootear (cold start) más que el timeout. Verificá:
- El zip incluye todas las dependencias (si tu agente usa boto3, agregalo a `requirements.txt`)
- El `main.py` arranca el HTTP server en `0.0.0.0:8080`
- Los logs en CloudWatch del runtime para ver errores de startup

---

## Próximos pasos después de fase 0

Cuando fase 0 esté operando:

1. **Agregar más agentes** copiando el `_template`
2. **Migrar a fase 1** cuando necesites: tools-Lambda, container mode (Docker), MCP server, gateways custom, Cedar policies
3. **Mejorar la operación**: SLOs, runbooks, drift detection (ver `docs/01_IMPROVEMENTS_AND_FUTURE_WORK.md` del repo global si tienes acceso)

## Soporte

- Issues con el código: documentalo en el repo `infra-agentcore` de tu group
- Issues con AWS quotas: AWS Support
- Issues con GitLab: GitLab Support o foros públicos
