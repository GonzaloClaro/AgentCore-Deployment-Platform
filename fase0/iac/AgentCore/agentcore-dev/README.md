# agentcore-dev

> **Tipo:** Proyecto deployable Terraform (cuenta `dev-agenticplatform`)
> **State:** GitLab-managed Terraform state (per-project)

Este proyecto es uno de los 3 deployables (dev/qa/prd) que ejecutan Terraform con módulos del repo `infra-agentcore`. Es **slim**: solo contiene los valores por cuenta y dispara el pipeline downstream.

## Estructura

```
.gitlab-ci.yml          # include de Compose-AgentCore/pipeline_infra.yml
env-defaults.yaml       # VPC IDs, subnets, KMS keys, account_id, IAM defaults
backend.tf              # generado dinámicamente (GitLab HTTP backend)
providers.tf            # provider aws con assume-role a cuenta DEV
versions.tf             # pin terraform >=1.6
README.md
```

## Cómo funciona

1. El pipeline upstream (de `AgentPlatform`) genera `terraform.auto.tfvars.json` y `composition_name.txt` y dispara este proyecto via `trigger_iac` con esos artefactos.
2. El pipeline aquí ejecuta `terraform init` con backend GitLab managed state usando un nombre de state por workload + composición (key: `agentcore-dev-${COMPOSITION_NAME}-${UPSTREAM_PROJECT}`).
3. Hace `terraform plan` y `terraform apply` desde `compositions/${COMPOSITION_NAME}/` (referenciado vía `git::` con tag de `infra-agentcore`).
4. Los outputs (runtime ARN, alias ARN, etc.) quedan disponibles para el smoke test del pipeline upstream.

## State

GitLab-managed state. Cada workload tiene su propio nombre de state:
```
state name: agentcore-dev-<composition>-<upstream-project-path-slug>
```

## Promoción

- `agentcore-dev` consume `infra-agentcore@main` (latest).
- Para promover un cambio testeado: hacer release `vX.Y.Z` en `infra-agentcore`, y luego cambiar `INFRA_REF` en `agentcore-qa` y `agentcore-prd`.

## Variables CI/CD necesarias (configuradas en GitLab project settings)

| Variable | Tipo | Descripción |
|---|---|---|
| `AWS_ROLE_ARN` | masked | Role IAM en cuenta DEV con permisos de deploy |
| `GITLAB_TOKEN_READ_API` | masked | Token con scope read_api para clonar `infra-agentcore` privado |
