# Manifest Reference — Fase 0

> Diccionario completo de campos del `manifest.yaml` de fase 0. Schema simplificado respecto al global: solo zip mode, sin tools, sin gateways custom, sin Cedar policies.

## Estructura completa

```yaml
apiVersion: v1
kind: Agent

metadata:
  name: hello-agent                     # required, kebab-case
  capability: platform-test             # required, kebab-case
  owner: ops@empresa.com                # required, email del owner técnico
  description: "Agente de pruebas"      # optional
  tags:                                 # optional, lista de tags AWS
    - team-platform
    - mvp

spec:
  composition: agent-base-zip           # required, una de las 2 válidas

  runtime:
    entrypoint: main.py                 # required, archivo Python que arranca HTTP server
    runtime_version: PYTHON_3_13        # optional (default: PYTHON_3_13)
    env:                                # optional, env vars al runtime
      LOG_LEVEL: INFO

  models:                               # optional, lista de LLMs
    - alias: PRIMARY
      provider: bedrock
      bedrock:
        model_id: amazon.nova-micro-v1:0
        region: us-east-1

  memory:                               # solo agent-with-kb-zip
    strategy: summarization

  knowledge_base:                       # solo agent-with-kb-zip
    embedding: amazon.titan-embed-text-v2:0
    sources_file: kb/data_sources.yaml

  prompts:                              # optional, prompts versionados
    - file: prompts/system.yaml
      alias: SYSTEM_PROMPT_ARN

  observability:                        # optional
    enabled: true

  features:                             # optional, feature flags
    enable_observability: true
```

## Campos por sección

### `apiVersion` (required, string)
- Único valor: `v1`

### `kind` (required, string)
- Único valor: `Agent`

### `metadata` (required, object)

| Campo | Tipo | Required | Validación | Descripción |
|-------|------|----------|------------|-------------|
| `name` | string | sí | `^[a-z][a-z0-9-]{2,40}$` | Nombre del agente, kebab-case |
| `capability` | string | sí | `^[a-z][a-z0-9-]{2,40}$` | Equipo/dominio dueño |
| `owner` | string | sí | — | Email del owner técnico |
| `description` | string | no | — | Descripción libre |
| `tags` | list[string] | no | — | Tags AWS para identificar recursos |

### `spec.composition` (required, enum)

Una de las **2 composiciones de fase 0**:

| Composición | Recursos que crea | Cuándo usarla |
|-------------|-------------------|----------------|
| `agent-base-zip` | runtime + observability | Agente sin estado ni KB. Uso típico: agentes que solo invocan modelos, sin persistencia |
| `agent-with-kb-zip` | runtime + memory + knowledge_base + observability | Chatbot RAG con memoria conversacional + base de conocimiento |

### `spec.runtime` (required, object)

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `entrypoint` | string | — (required) | Archivo Python en `src/` que arranca el HTTP server (ej: `main.py`) |
| `runtime_version` | string | `PYTHON_3_13` | Versión Python soportada por AgentCore |
| `env` | map[string]string | `{}` | Variables de entorno inyectadas al runtime |

**Convenciones del entrypoint**:
- El archivo debe iniciar un HTTP server en `0.0.0.0:8080`
- Debe responder a `GET /ping` con status 200
- Debe responder a `POST /invocations` con la lógica del agente
- Sin dependencias system-level (solo Python + lo que pip instala desde `requirements.txt`)

### `spec.models` (optional, list)

Lista de modelos LLM. Cada uno produce env vars con prefijo del alias:
- `<ALIAS>_MODEL_ID`
- `<ALIAS>_MODEL_PROVIDER`
- `<ALIAS>_MODEL_REGION`
- `<ALIAS>_MODEL_INFERENCE_PROFILE_ARN` (si aplica)
- Para Azure: `<ALIAS>_MODEL_ENDPOINT`, `<ALIAS>_MODEL_DEPLOYMENT`, etc.

#### Item de la lista

| Campo | Tipo | Required | Descripción |
|-------|------|----------|-------------|
| `alias` | string | sí | UPPER_SNAKE_CASE. Ej: `PRIMARY`, `FALLBACK` |
| `provider` | enum | sí | `bedrock` \| `azure` |
| `bedrock` | object | si provider=bedrock | Sub-bloque con `model_id`, `region`, `inference_profile_arn` |
| `azure` | object | si provider=azure | Sub-bloque con `endpoint`, `deployment`, `api_version`, `api_key_secret_var` |

#### Sub-bloque `bedrock`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `model_id` | string | Bedrock model ID. Para cross-region inference profile usar prefijo `us.` o `eu.` |
| `region` | string | Region AWS (default: `aws_region` del env-defaults) |
| `inference_profile_arn` | string | ARN de inference profile dedicado (mutuamente excluyente con `model_id`) |

#### Sub-bloque `azure`

| Campo | Tipo | Required | Descripción |
|-------|------|----------|-------------|
| `endpoint` | string (URI) | sí | Azure OpenAI endpoint URL |
| `deployment` | string | sí | Nombre del deployment Azure |
| `api_version` | string | sí | Ej: `2024-08-01-preview` |
| `api_key_secret_var` | string | sí | Nombre de la CI variable masked con la API key (la sube `upload_secret`) |
| `model_id` | string | no | Model id subyacente (gpt-4o, etc.) |

### `spec.memory` (optional, object) — solo agent-with-kb-zip

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `strategy` | enum | `summarization` | `summarization` \| `semantic` \| `user-preference` \| `none` |

### `spec.knowledge_base` (optional, object) — solo agent-with-kb-zip

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `embedding` | string | `amazon.titan-embed-text-v2:0` | Modelo de embedding |
| `sources_file` | string | — | Path al YAML con sources S3 (relativo al manifest) |

### `spec.prompts` (optional, list)

Lista de prompts versionados via Bedrock Prompt Management. Cada uno se publica via SDK y produce una env var con el ARN versionado.

| Campo | Tipo | Required | Descripción |
|-------|------|----------|-------------|
| `file` | string | sí | Path al YAML del prompt (relativo al manifest) |
| `alias` | string | no | Env var inyectada al runtime con el ARN del prompt |

### `spec.observability` (optional, object)

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Crea CloudWatch log group + dashboard del runtime |

### `spec.features` (optional, object)

Mapa de feature flags booleanos.

| Flag | Default | Descripción |
|------|---------|-------------|
| `enable_observability` | `true` | Activa el módulo observability |

## Diferencias respecto al manifest global

| Sección global | Fase 0 |
|----------------|--------|
| `kind: Workload` | `kind: Agent` |
| Composiciones disponibles: 7 | Composiciones disponibles: 2 |
| `metadata.kind` ("agents", "mcp", "tools") | No existe — siempre agent |
| `metadata.target_shard` | No existe — un solo shard por env |
| `spec.runtime.memory_strategy` | Movido a `spec.memory.strategy` |
| `spec.gateway_targets` | No existe |
| `spec.gateway_policies` | No existe |
| `spec.oauth_provider` | No existe |
| `spec.runtime_iam` | No existe (siempre default_role_arn) |
| `spec.tool` | No existe |

## Ejemplos completos

### Ejemplo 1: agent-base-zip simple

```yaml
apiVersion: v1
kind: Agent
metadata:
  name: hello-world
  capability: platform-test
  owner: gonzaloclarom@gmail.com
spec:
  composition: agent-base-zip
  runtime:
    entrypoint: main.py
    env:
      LOG_LEVEL: INFO
  models:
    - alias: PRIMARY
      provider: bedrock
      bedrock:
        model_id: amazon.nova-micro-v1:0
        region: us-east-1
```

### Ejemplo 2: agent-with-kb-zip (chatbot RAG)

```yaml
apiVersion: v1
kind: Agent
metadata:
  name: docs-assistant
  capability: knowledge
  owner: gonzaloclarom@gmail.com
spec:
  composition: agent-with-kb-zip
  runtime:
    entrypoint: main.py
    env:
      LOG_LEVEL: INFO
      RAG_TOP_K: "5"
  models:
    - alias: PRIMARY
      provider: bedrock
      bedrock:
        model_id: us.anthropic.claude-3-5-haiku-20241022-v1:0
  memory:
    strategy: summarization
  knowledge_base:
    embedding: amazon.titan-embed-text-v2:0
    sources_file: kb/sources.yaml
  prompts:
    - file: prompts/system.yaml
      alias: SYSTEM_PROMPT_ARN
```

`kb/sources.yaml`:
```yaml
sources:
  - name: docs
    bucket_arn: arn:aws:s3:::my-docs-bucket
    inclusion_prefixes:
      - "documentation/"
```

### Ejemplo 3: agente con modelo Azure

```yaml
apiVersion: v1
kind: Agent
metadata:
  name: azure-test
  capability: platform-test
  owner: gonzaloclarom@gmail.com
spec:
  composition: agent-base-zip
  runtime:
    entrypoint: main.py
  models:
    - alias: PRIMARY
      provider: azure
      azure:
        endpoint: https://my-instance.openai.azure.com/
        deployment: gpt-4o
        api_version: "2024-08-01-preview"
        api_key_secret_var: AZURE_OPENAI_API_KEY  # CI var, upload_secret la sube a Secrets Manager
        model_id: gpt-4o
```
