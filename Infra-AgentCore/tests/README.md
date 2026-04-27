# Terraform Tests

Tests para los módulos y composiciones de `Infra-AgentCore`.

## Niveles

### Nivel 1: `terraform validate` (sin AWS)
Detecta errores de sintaxis, variables no declaradas, refs rotas, type mismatches.

```bash
# Cada módulo
for m in modules/*/; do
  echo "→ $m"
  terraform -chdir="$m" init -backend=false
  terraform -chdir="$m" validate
done

# Cada composición
for c in compositions/*/; do
  echo "→ $c"
  terraform -chdir="$c" init -backend=false
  terraform -chdir="$c" validate
done
```

### Nivel 2: `terraform fmt -check`
Detecta inconsistencias de formato. Falla si hay archivos no formateados.

```bash
terraform fmt -check -recursive .
```

### Nivel 3: `terraform test` con `command = plan`
Tests declarativos en HCL bajo `tests/*.tftest.hcl`. Usa `command = plan` para no aplicar
recursos reales (que serían lentos/caros para AgentCore).

```bash
cd modules/runtime
terraform init -backend=false
terraform test
```

Lo que cubrimos por módulo:

| Módulo | Test | Qué valida |
|---|---|---|
| `runtime` | `defaults.tftest.hcl` | name correcto, alias 'live' creado, env_vars propagadas |
| `runtime-role` | `defaults.tftest.hcl` | role custom con managed/inline policies; bedrock invoke por default |
| `gateway-policy` | `defaults.tftest.hcl` | attach_mode válido, name pattern correcto |
| `agent-chatbot` (composition) | `defaults.tftest.hcl` | runtime_role no se crea por default; sí cuando se declara runtime_iam |

## Pipeline CI

El pipeline `pipeline_infra_tests.yml` (en Compose-AgentCore) corre:
1. `terraform fmt -check -recursive`
2. `terraform validate` en todos los módulos y composiciones
3. `terraform test` en módulos clave

Trigger: en cada MR que toque `Infra-AgentCore/`.
