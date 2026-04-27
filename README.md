# AgentPlatform Deployment

> Reference architecture para desplegar agentes de IA y MCP servers sobre **AWS Bedrock AgentCore** con un patrón manifest-driven, multi-cuenta y multi-ambiente.

Plataforma diseñada para que un dev de capability declare su workload en un `manifest.yaml` y todo lo demás —build de imagen, escaneo de vulnerabilidades, render de Terraform, deploy multi-cuenta— se haga automáticamente vía pipelines CI/CD.

## TL;DR — qué hay aquí

Un sistema completo de deployment para agentes de IA pensado como **5 repos lógicos** que se acoplan vía contratos:

| Repo lógico | Rol | Contenido |
|-------------|-----|-----------|
| [`AgentPlatform/`](AgentPlatform/) | Workloads | Manifests + código de los agentes/MCPs |
| [`Componentes-AgentCore/`](Componentes-AgentCore/) | Componentes CI/CD reutilizables | Lógica Python + templates GitLab |
| [`Compose-AgentCore/`](Compose-AgentCore/) | Orquestación | Pipelines productivos (YAML) |
| [`Infra-AgentCore/`](Infra-AgentCore/) | Terraform | Modules + compositions + foundation |
| [`iac/AgentCore/agentcore-{dev,qa,prd}/`](iac/AgentCore/) | Deployables | State Terraform por ambiente |

**📖 Para entender cómo encajan, lee [`docs/resumen.md`](docs/resumen.md).** Cubre cada repo en detalle, los 4 archivos canónicos de un module Terraform, cómo se construyen las compositions, y el flujo end-to-end desde un `git push` hasta los recursos AWS creados.

## Stack técnico

- **AWS Bedrock AgentCore** (servicio de runtime para agentes de IA)
- **Terraform `>= 1.9`** con provider `hashicorp/aws ~> 6.42` (también compatible con OpenTofu)
- **Python 3.12** para la lógica de los componentes CI
- **GitLab CI/CD components** (templates publicables vía `include: - component:`)
- **Docker buildx** ARM64 para imágenes
- **Bedrock Knowledge Base** + **S3 Vectors** para RAG
- **Cedar policies** para autorización en gateways

## Patrones destacados

- **Manifest-driven deployment**: el dev solo edita un YAML; el pipeline hace el resto.
- **Modules + compositions**: arquetipos de workload (`agent-chatbot`, `agent-with-tools`, `mcp-server`, etc.) construidos como composiciones de modules reutilizables. Un archivo `.tf` por module enchufado para que sea trivial leer qué tiene cada arquetipo.
- **Foundation separado de workloads**: KMS keys, IAM roles base y los 3 default gateways viven en `foundation/` con state Terraform aislado, así un workload no puede borrar accidentalmente la base.
- **Promoción dev → qa → prd** con manual approval entre QA y PRD.
- **Defensa en profundidad en PRD**: deny policy explícita sobre `bedrock-agentcore:Delete*` para el role del pipeline + `emergency_destroyer` role separado con MFA + lifecycle protection.
- **Determinismo del provider**: `~> 6.42.0` fijado + `.terraform.lock.hcl` committeado.

## Estructura del repo

```
.
├── AgentPlatform/          # workloads (agentes, MCPs, tools)
├── Componentes-AgentCore/  # piezas reutilizables de CI/CD (Python + YAML)
├── Compose-AgentCore/      # pipelines productivos (cero Python)
├── Infra-AgentCore/        # código Terraform (sin state propio)
│   ├── foundation/         # bootstrap + default-gateways + vpc-endpoints
│   ├── modules/            # piezas Lego
│   └── compositions/       # arquetipos = ensamble de modules
├── iac/AgentCore/          # deployables por ambiente (state Terraform)
│   ├── agentcore-dev/
│   ├── agentcore-qa/
│   └── agentcore-prd/
├── docs/                   # documentación (comienza por resumen.md)
└── tasks/                  # planes y lessons-learned de iteraciones
```

## Documentación

| Doc | Contenido |
|-----|-----------|
| **[`docs/resumen.md`](docs/resumen.md)** | **Comienza aquí**: explicación end-to-end de los 5 repos y el flujo de despliegue |
| **[`docs/08_TUTORIAL_DEVOPS.md`](docs/08_TUTORIAL_DEVOPS.md)** | Tutorial paso a paso para el equipo de plataforma: bootstrap, primer agente, troubleshooting, operación diaria |
| [`PLAN.md`](PLAN.md) | Roadmap por fases del proyecto |
| [`MANIFEST_REFERENCE.md`](MANIFEST_REFERENCE.md) | Schema completo del manifest opinado |
| [`MULTI_ACCOUNT.md`](MULTI_ACCOUNT.md) | Setup multi-cuenta AWS (dev/qa/prd) |
| [`CI_VARIABLES.md`](CI_VARIABLES.md) | Variables CI/CD requeridas |
| [`RUNBOOK_DESTROY_PRD.md`](RUNBOOK_DESTROY_PRD.md) | Procedimiento de destroy en PRD |
| [`docs/01_IMPROVEMENTS_AND_FUTURE_WORK.md`](docs/01_IMPROVEMENTS_AND_FUTURE_WORK.md) | Backlog de mejoras priorizado por disparador |
| [`docs/04_ARCHITECTURE_COMPONENTS.md`](docs/04_ARCHITECTURE_COMPONENTS.md) | Componentes de la arquitectura |
| [`docs/05_FLOWS_AND_DIAGRAMS.md`](docs/05_FLOWS_AND_DIAGRAMS.md) | Diagramas de flujo |
| [`docs/07_QUOTAS.md`](docs/07_QUOTAS.md) | Quotas AWS relevantes |

## Notas para quien llega frío

- **Monorepo intencional**: el sistema está diseñado como 5 repos GitLab separados (las pipelines hacen `include: - project: Componentes/...` y `git clone .../iac/...`). Aquí viven juntos en una sola raíz para que sea más fácil leerlo en GitHub. Las cross-references entre pipelines apuntan a paths GitLab que **no existen** en GitHub — los workflows CI no corren tal cual aquí.
- **Account ID `111122223333`**: aparece en varios lugares (manifests de ejemplo, tests, JSON-schemas). Es el **AWS sample account ID** oficial usado en toda la doc de AWS — equivalente a `example.com` para URLs. No es info real.
- **Estado del código**: la infra Terraform pasa `terraform validate` end-to-end contra el provider `hashicorp/aws ~> 6.42`. Los recursos AgentCore que usa están en GA. Los componentes Python tienen unit tests bajo `Componentes-AgentCore/tests/`. El sistema **no está deployado** públicamente — el repo es código + diseño.

## Validar localmente

Para validar el código Terraform:

```bash
cd Infra-AgentCore
brew install opentofu  # o: brew install terraform
./scripts/tf-check.sh           # fmt -check + validate end-to-end
./scripts/tf-check.sh fix       # auto-format
```

Para correr los tests Python de los componentes:

```bash
cd Componentes-AgentCore
pip install -r src/requirements.txt
pytest tests/
```

## Licencia

Sin licencia explícita — código de referencia. Si te interesa reusar partes específicas, abre un issue.
