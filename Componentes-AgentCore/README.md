# Componentes-AgentCore

> **Dominio CI/CD:** `agentcore`
> **Tipo:** Componentes reutilizables (siguen framework de la organización)

Repositorio de **componentes de CI/CD** del dominio `agentcore`. Cada subdirectorio de `templates/` es un **subdominio** que expone un job genérico, agnóstico y reutilizable. La lógica vive en `src/<subdominio>/<action>.py`.

## Reglas duras (framework)

- **NO** se definen `rules`, `tags` ni `default:` global aquí. Eso vive en `Compose-AgentCore`.
- **Inputs tipados** con `spec.inputs` y separador `---`.
- **Nombres de jobs dinámicos** vía `"$[[ inputs.job_name ]]"`.
- **Lógica en Python** bajo `src/`, no en bash inline.
- **Branching:** `main` productivo, desarrollos en `feat/***`, MR a `main`.

## Estructura

```
templates/                    # consumibles vía include: - component:
  includes/base/              # bloques !reference compartidos
  <subdominio>/template.yml   # un componente publicable
src/                          # lógica Python ejecutada por los jobs
  <subdominio>/<action>.py
  utils/                      # helpers compartidos (aws, manifest, gitlab)
config_files/                 # YAML/JSON de configuración (no de pipeline)
  shared/
  <subdominio>/
```

## Subdominios disponibles

| Subdominio | Acción | Descripción |
|---|---|---|
| `validate_manifest` | `validate.py` | Valida `manifest.yaml` contra JSON-schema |
| `package_artifact` | `package.py` | Zipea `src/` del workload y sube a S3 (artefacto auditable) |
| `build_image` | `build.py` | `docker buildx --platform linux/arm64` y push a ECR |
| `scan_image` | `scan.py` | Escaneo de vulnerabilidades de la imagen (gate) |
| `upload_secret` | `upload.py` | CI variable masked → AWS Secrets Manager (ARN devuelto) |
| `render_tfvars` | `render.py` | `manifest + env-defaults` → `terraform.auto.tfvars.json` + `composition_name.txt` |
| `trigger_iac` | `trigger.py` | Multi-project trigger al deployable `agentcore-{env}` |
| `publish_prompt` | `publish.py` | Registra/versiona prompt en Bedrock Prompt Management |
| `publish_leanix` | `publish.py` | Publica metadata del workload a LeanIX |
| `smoke_test` | `smoke.py` | Invoca `/ping` del runtime tras apply |
| `deploy_agent` | `deploy.py` | Macro: empaqueta los pasos típicos para un agente |
| `deploy_mcp` | `deploy.py` | Macro: empaqueta los pasos típicos para un MCP server |

## Tabla de inputs (resumen)

Todos los componentes aceptan al menos:

| Input | Tipo | Default | Descripción |
|---|---|---|---|
| `job_name` | string | — | Nombre del job en el pipeline consumidor |
| `stage` | string | varía | Stage donde correrá el job |
| `image_runner` | string | `""` | Imagen Docker del runner |
| `environment` | string | `dev` | Ambiente destino (`dev`/`qa`/`prd`) |

Inputs específicos por componente: ver el `spec.inputs` en cada `templates/<subdominio>/template.yml`.

## Ejemplo de uso desde Compose

```yaml
include:
  - component: $CI_SERVER_FQDN/Componentes/agentcore/validate_manifest@main
    inputs:
      job_name: validate-manifest
      stage: validate
      image_runner: $IMAGE_BASE
      manifest_path: agents/customer-support/chatbot-tier1/manifest.yaml
```

## Versionado

- Tags semver: `v1.2.3`
- Compose puede consumir `@main`, `@v1.2.3`, `@<sha>`, `~latest`
- Cambios breaking → bump major + nota en CHANGELOG

## Desarrollo

```bash
git checkout -b feat/<subdominio>-<descripcion>
# editar templates/<subdominio>/template.yml + src/<subdominio>/<action>.py
# probar con un pipeline de prueba que incluya el componente
git push -u origin feat/...
# MR a main
```
