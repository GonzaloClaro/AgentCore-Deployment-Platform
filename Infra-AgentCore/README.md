# Infra-AgentCore

> **Tipo:** Código Terraform (módulos + composiciones, **sin state**)
> **Consumido por:** repos deployables `iac/AgentCore/agentcore-{dev,qa,prd}`

Este repo contiene los **módulos Terraform** del dominio AgentCore y las **composiciones** que combinan módulos para arquetipos comunes (chatbot, RAG, MCP server, full). Versionado con tags semver; los deployables referencian un tag específico.

## Patrón: módulos + composiciones por archivo

### Módulos (`modules/<nombre>/`)

Cada módulo modela **un** recurso o componente AgentCore (runtime, memory, observability, etc.) con la estructura canónica:

```
modules/<nombre>/
  main.tf        # los resources del componente
  variables.tf   # inputs tipados
  outputs.tf     # outputs reutilizables
  versions.tf    # required_version + providers
```

Estos módulos NO se modifican típicamente — son las "piezas Lego". Si encuentras que un módulo no soporta un caso, primero considera agregar una variable opcional antes de bypasearlo.

### Composiciones (`compositions/<nombre>/`)

Cada composición es un **ensamble** de módulos para un arquetipo concreto. Para que sea fácil **leer qué tiene cada composición** y **crear nuevas**, usamos **un archivo `.tf` por cada componente que enchufa**:

```
compositions/agent-chatbot/
  main.tf            # solo terraform/provider/locals (sin recursos)
  runtime.tf         # module "runtime"
  memory.tf          # module "memory"
  observability.tf   # module "observability" con count = features.enable_observability ? 1 : 0
  variables.tf       # inputs tipados
  outputs.tf         # outputs expuestos al deployable
```

**Ventaja:** para crear una composición nueva, copias la más cercana, agregas/borras archivos `.tf`. No tienes que leer un `main.tf` gigante.

## Composiciones disponibles

| Composición | Componentes incluidos | Uso típico |
|---|---|---|
| `agent-chatbot` | runtime + memory + observability | Chatbot simple |
| `agent-with-kb` | + knowledge_base | RAG con documentos S3 |
| `agent-with-tools` | runtime + memory + gateway_targets + observability | Agente con tools externas via gateway |
| `mcp-server` | runtime + oauth_provider + gateway_targets + observability | MCP server con OAuth |
| `agent-full` 🎯 | TODO con flags | Cualquier combinación rara |

> **`agent-full` es la "playground":** tiene todos los componentes posibles. Cada uno se enciende/apaga con un flag booleano en `spec.features` del manifest. Si tu workload no calza con ninguna composición predefinida, **usa `agent-full` y configura solo lo que necesitas**.

## Cómo crear una composición custom

1. **Decide si la necesitas.** Antes, considera si `agent-full` con flags resuelve tu caso.
2. **Copia la composición más cercana** a `compositions/<nuevo-nombre>/`.
3. **Agrega o borra archivos `.tf`** por cada componente que quieras incluir/excluir.
4. **Actualiza `outputs.tf`** para expongas lo que el deployable o smoke test necesita.
5. **Agrega `<nuevo-nombre>` al enum del JSON-schema** en `Componentes-AgentCore/config_files/validate_manifest/manifest.schema.json` (campo `spec.composition.enum`).
6. **Documenta** en `config_files/render_tfvars/composition_map.yml` qué campos del manifest espera.

## Cómo levantar **un solo componente** rápidamente

Si solo quieres probar un módulo aislado (ej: solo `memory` para experimentar):

```hcl
# main.tf en cualquier directorio fuera del repo
module "memory_test" {
  source = "git::ssh://git@gitlab.example.com/iac/AgentCore/infra-agentcore.git//modules/memory?ref=main"

  name = "test-memory"
  strategies = [{
    name = "summarization"
    type = "SUMMARIZATION"
    namespaces = ["/"]
    configuration = null
  }]
}
```

`terraform init && terraform apply` y listo. Sin pipeline, sin Compose. Útil para debug y experimentación local.

## Foundation (apply manual una vez por cuenta)

```
foundation/
  bootstrap/         # KMS, S3 artifact buckets, IAM roles base — UNA SOLA VEZ por cuenta
  default-gateways/  # los 3 gateways por defecto (3LO, 2LO, SigV4) — al inicio + cuando cambien
  vpc-endpoints/     # endpoints VPC privados — al inicio si runtime corre en VPC
```

Los workloads NO crean gateways; solo agregan **targets** vía módulo `gateway-target`. Los IDs de los 3 default gateways viven en `iac/AgentCore/agentcore-{env}/env-defaults.yaml` después de aplicar foundation.

## Uso desde un deployable

```hcl
# Generado dinámicamente por render_tfvars en pipeline
module "this" {
  source = "git::ssh://git@gitlab.example.com/iac/AgentCore/infra-agentcore.git//compositions/agent-with-kb?ref=v1.2.3"
  # variables vienen de terraform.auto.tfvars.json
}
```

## Issues conocidas del provider AWS Terraform

- **`aws_bedrockagentcore_gateway_target` sin `grant_type` para OAuth** (hashicorp/terraform-provider-aws#46128). Workaround: `local-exec` con AWS CLI (`use_native_resource = false`).
- **ENIs huérfanas en destroy de `aws_bedrockagentcore_agent_runtime`** (#45099). Documentar runbook de cleanup.

## Versionado

- `main` = en desarrollo (consume `agentcore-dev`).
- Tags `vMAJOR.MINOR.PATCH` para releases — `agentcore-qa` y `agentcore-prd` siempre consumen tags inmutables.
- Cambios breaking → bump major + nota en CHANGELOG.

## Mapping flags ↔ componentes (en `agent-full`)

| Flag en `spec.features` | Activa | Default |
|---|---|---|
| `enable_observability` | `observability.tf` | `true` |
| `enable_kb` | `knowledge_base.tf` (si hay sources) | `false` |
| `enable_tools` | `gateway_targets.tf` (si hay targets) | `false` |
| `enable_prompts_terraform` | `prompts.tf` (si prefieres TF sobre `publish_prompt`) | `false` |

`runtime.tf` y `memory.tf` están **siempre activos** — son el core del agente. Para apagar memory, usa `spec.runtime.memory_strategy: none`.
