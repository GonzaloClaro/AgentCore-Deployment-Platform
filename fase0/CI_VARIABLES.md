# CI Variables — Fase 0

> Variables CI/CD necesarias para correr los pipelines de fase 0 en GitLab. Subset reducido del documento global.

## Convenciones

- **Masked**: la variable no aparece en logs (✅ activar para todo lo que sea secreto/token)
- **Protected**: la variable solo está disponible en branches/tags protegidos
- **Scope=environment**: la variable solo aplica al environment declarado por el job

## Variables a nivel **Group** del proyecto fase 0

Configurar en `Group → Settings → CI/CD → Variables` del grupo top-level donde subas fase 0.

### AWS — credenciales por ambiente (vía OIDC)

| Variable | Masked | Protected | Scope | Valor / Descripción |
|----------|--------|-----------|-------|---------------------|
| `AWS_ROLE_ARN_DEV` | ✅ | ❌ | `dev` | ARN del IAM role asumido por OIDC en cuenta dev |
| `AWS_ROLE_ARN_QA` | ✅ | ✅ | `qa` | Idem para qa |
| `AWS_ROLE_ARN_PRD` | ✅ | ✅ | `prd` | Idem para prd |
| `AWS_ACCOUNT_ID_DEV` | ✅ | ❌ | `dev` | Account ID dev (12 dígitos) |
| `AWS_ACCOUNT_ID_QA` | ❌ | ✅ | `qa` | Account ID qa |
| `AWS_ACCOUNT_ID_PRD` | ❌ | ✅ | `prd` | Account ID prd |
| `AWS_REGION` | ❌ | ❌ | `*` | Region AWS (ej: `us-east-1`) |

### Runner

| Variable | Masked | Protected | Scope | Valor / Descripción |
|----------|--------|-----------|-------|---------------------|
| `ORG_RUNNER_IMAGE` | ❌ | ❌ | `*` | Imagen Docker del runner (ej: `python:3.12-slim`) |

### Modelos Azure (solo si algún agente usa provider=azure)

| Variable | Masked | Protected | Scope | Valor / Descripción |
|----------|--------|-----------|-------|---------------------|
| `AZURE_OPENAI_API_KEY` | ✅ | ✅ | `dev`, `qa`, `prd` | API key de Azure OpenAI. `upload_secret` la sube a Secrets Manager |

> Si tenés múltiples agentes con keys distintas: `AZURE_OPENAI_API_KEY_<ALIAS>` y referenciás desde el manifest con `api_key_secret_var: AZURE_OPENAI_API_KEY_<ALIAS>`.

## Variables NO necesarias en fase 0 (vs documento global)

Las siguientes variables están en `CI_VARIABLES.md` global pero NO se usan en fase 0:

| Variable | Por qué no aplica |
|----------|-------------------|
| `LEANIX_ENDPOINT`, `LEANIX_API_TOKEN` | Sin catálogo en fase 0 |
| `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` | Sin OAuth providers (no MCP server) |
| `GITLAB_TOKEN_READ_API` | Solo necesario si los componentes hacen self-clone |

## Subset mínimo viable

Para arrancar con un solo ambiente y modelos Bedrock (sin Azure):

```
AWS_ROLE_ARN_DEV       (✅ masked)
AWS_ACCOUNT_ID_DEV     (✅ masked)
AWS_REGION             (=us-east-1)
ORG_RUNNER_IMAGE       (=python:3.12-slim)
```

4 variables, listo para correr el primer pipeline.

## Setup OIDC entre GitLab y AWS

Pre-requisito: tener configurado el OIDC trust entre tu GitLab y AWS. Pasos resumidos:

### 1. En AWS, crear el OIDC provider

```bash
THUMBPRINT=$(echo | openssl s_client -servername gitlab.com -showcerts -connect gitlab.com:443 2>/dev/null \
  | openssl x509 -fingerprint -noout -sha1 | sed 's/.*=//' | tr -d ':' | tr 'A-Z' 'a-z')

aws iam create-open-id-connect-provider \
  --url "https://gitlab.com" \
  --client-id-list "https://gitlab.com" \
  --thumbprint-list "$THUMBPRINT"
```

### 2. Crear IAM role con trust policy

`/tmp/trust.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/gitlab.com" },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": { "gitlab.com:aud": "https://gitlab.com" },
        "StringLike": { "gitlab.com:sub": "project_path:<TU-NAMESPACE>/*" }
      }
    }
  ]
}
```

```bash
aws iam create-role \
  --role-name gitlab-deployer-dev \
  --assume-role-policy-document file:///tmp/trust.json

aws iam attach-role-policy \
  --role-name gitlab-deployer-dev \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

### 3. En el pipeline, los jobs ya tienen `id_tokens` configurado

```yaml
my-job:
  id_tokens:
    GITLAB_OIDC_TOKEN:
      aud: https://gitlab.com
  before_script:
    - export AWS_ROLE_ARN=$AWS_ROLE_ARN_DEV
    - export AWS_WEB_IDENTITY_TOKEN_FILE=$(mktemp)
    - echo "$GITLAB_OIDC_TOKEN" > $AWS_WEB_IDENTITY_TOKEN_FILE
    - aws sts get-caller-identity
```

## Checklist de bootstrap inicial (orden recomendado)

- [ ] Crear cuentas AWS (al menos dev) y obtener Account IDs
- [ ] Crear IAM role + OIDC provider en AWS (paso anterior)
- [ ] Crear group y proyectos en GitLab (ver `TUTORIAL.md`)
- [ ] Configurar las 4 variables mínimas en el group
- [ ] Aplicar foundation/bootstrap en cuenta dev (manual primer apply)
- [ ] Pushear primer agente y validar que la pipeline corre end-to-end
