# Documentación del Framework

Carpeta única de documentación del framework de despliegue de agentes IA sobre AWS Bedrock AgentCore para grandes organizaciones.

## Mapa de lectura por rol

### Si eres **decisor / sponsor / dirección**
Lee en este orden:
1. **[06_EXECUTIVE_OVERVIEW.md](./06_EXECUTIVE_OVERVIEW.md)** — visión, justificación, compromisos por área, debilidades, futuro.
2. **[02_PHASED_IMPLEMENTATION_PLAN.md](./02_PHASED_IMPLEMENTATION_PLAN.md)** §"Tabla resumen" — cuándo se ve valor.
3. **[07_QUOTAS.md](./07_QUOTAS.md)** §"Capacity planning calculadora" — proyección de cuentas AWS necesarias.

### Si eres **Tech Lead del equipo de plataforma**
Lee en este orden:
1. **[04_ARCHITECTURE_COMPONENTS.md](./04_ARCHITECTURE_COMPONENTS.md)** — entender el modelo mental.
2. **[03_INDEX_GLOSSARY.md](./03_INDEX_GLOSSARY.md)** — saber dónde está cada cosa.
3. **[02_PHASED_IMPLEMENTATION_PLAN.md](./02_PHASED_IMPLEMENTATION_PLAN.md)** — qué construir y cuándo.
4. **[08_TUTORIAL_DEVOPS.md](./08_TUTORIAL_DEVOPS.md)** — paso a paso de operación de la plataforma.
5. **[01_IMPROVEMENTS_AND_FUTURE_WORK.md](./01_IMPROVEMENTS_AND_FUTURE_WORK.md)** — backlog priorizado.
6. **[05_FLOWS_AND_DIAGRAMS.md](./05_FLOWS_AND_DIAGRAMS.md)** — flujos productivos y troubleshooting.

### Si eres **dev de un equipo consumidor**
Lee en este orden:
1. `MANIFEST_REFERENCE.md` (raíz del repo) — qué puedes configurar en tu workload.
2. **[03_INDEX_GLOSSARY.md](./03_INDEX_GLOSSARY.md)** — tabla "quiero hacer X → archivo Y".
3. `AgentPlatform/agents/_template/` — plantilla copy/paste de tu primer agente.
4. **[05_FLOWS_AND_DIAGRAMS.md](./05_FLOWS_AND_DIAGRAMS.md)** — qué pasa cuando haces push.

### Si eres **CloudOps / DevOps de plataforma**
Lee en este orden:
1. **[08_TUTORIAL_DEVOPS.md](./08_TUTORIAL_DEVOPS.md)** — tutorial completo de operación, desde bootstrap hasta troubleshooting.
2. **[07_QUOTAS.md](./07_QUOTAS.md)** — cuotas, sharding, capacity planning.
3. `MULTI_ACCOUNT.md` (raíz) — cómo agregar cuenta nueva.
4. `RUNBOOK_DESTROY_PRD.md` (raíz) — destroys en PRD.
5. **[04_ARCHITECTURE_COMPONENTS.md](./04_ARCHITECTURE_COMPONENTS.md)** §"Foundation" y §"Deployables".

### Si eres **Seguridad / Compliance**
Lee en este orden:
1. **[06_EXECUTIVE_OVERVIEW.md](./06_EXECUTIVE_OVERVIEW.md)** §"Compromisos requeridos por área" → "Seguridad".
2. **[05_FLOWS_AND_DIAGRAMS.md](./05_FLOWS_AND_DIAGRAMS.md)** §7 (Cedar policies) y §10 (Destroy en PRD).
3. `RUNBOOK_DESTROY_PRD.md` (raíz).
4. `MANIFEST_REFERENCE.md` §3.bis (Cedar) y §3.ter (IAM runtime).

### Si eres **FinOps**
Lee en este orden:
1. **[07_QUOTAS.md](./07_QUOTAS.md)** — capacity planning + costos por shard.
2. `Componentes-AgentCore/config_files/allowed_models.yml` — whitelist de modelos (los costosos requieren tu approval).
3. **[01_IMPROVEMENTS_AND_FUTURE_WORK.md](./01_IMPROVEMENTS_AND_FUTURE_WORK.md)** §"Optimización y costos".

### Si eres **Equipo de Accesos (IAM/Identity)**
Lee en este orden:
1. **[06_EXECUTIVE_OVERVIEW.md](./06_EXECUTIVE_OVERVIEW.md)** §"Compromisos requeridos por área" → "Equipo de Accesos".
2. `MANIFEST_REFERENCE.md` §3.ter — cómo se consumen tus managed policies.
3. `Infra-AgentCore/foundation/bootstrap/` — IAM Deny PRD + emergency destroyer role.

---

## Inventario de archivos

| # | Archivo | Audiencia primaria | Tamaño | Foco |
|---|---|---|---|---|
| 0 | [README.md](./README.md) | Todos | corto | Este archivo |
| 1 | [01_IMPROVEMENTS_AND_FUTURE_WORK.md](./01_IMPROVEMENTS_AND_FUTURE_WORK.md) | Tech Lead, PM | mediano | Backlog priorizado por disparador |
| 2 | [02_PHASED_IMPLEMENTATION_PLAN.md](./02_PHASED_IMPLEMENTATION_PLAN.md) | Tech Lead, PM, sponsors | largo | 10 fases incrementales 0→9+ |
| 3 | [03_INDEX_GLOSSARY.md](./03_INDEX_GLOSSARY.md) | Todos los devs | mediano | Tabla "dónde está / qué significa" |
| 4 | [04_ARCHITECTURE_COMPONENTS.md](./04_ARCHITECTURE_COMPONENTS.md) | Tech Lead, devs platform | largo | Modelo mental: componentes / compose / módulos / composiciones |
| 5 | [05_FLOWS_AND_DIAGRAMS.md](./05_FLOWS_AND_DIAGRAMS.md) | Devs, SRE | largo | 10 flujos críticos con diagramas Mermaid |
| 6 | [06_EXECUTIVE_OVERVIEW.md](./06_EXECUTIVE_OVERVIEW.md) | Dirección, sponsors | largo | Por qué el enfoque + compromisos + futuro descentralizado |
| 7 | [07_QUOTAS.md](./07_QUOTAS.md) | CloudOps, FinOps, Tech Lead | largo | Quotas AgentCore + escenarios + sharding |
| 8 | [08_TUTORIAL_DEVOPS.md](./08_TUTORIAL_DEVOPS.md) | DevOps / Platform Engineers | largo | Tutorial paso a paso de operación: bootstrap, primer agente, troubleshooting, día a día |
| - | [resumen.md](./resumen.md) | Todos | mediano | Vista global: 5 repos, modules + compositions, flujo end-to-end |

## Otros docs en la raíz del proyecto

| Archivo | Cuándo |
|---|---|
| `PLAN.md` | Plan original aprobado (referencia histórica) |
| `MANIFEST_REFERENCE.md` | Diccionario de campos del `manifest.yaml` |
| `CI_VARIABLES.md` | Configuración GitLab |
| `MULTI_ACCOUNT.md` | Sharding multi-cuenta |
| `RUNBOOK_DESTROY_PRD.md` | Runbook de destroys |
| `.env.example` | Plantilla local |

## Cómo se mantiene esta documentación

- **Owner:** equipo de plataforma (Tech Lead).
- **Revisión:** cada fin de fase (al final de cada hito de `02_PHASED_IMPLEMENTATION_PLAN.md`).
- **Cambios sensibles** (compromisos por área, quotas, sharding):
  - PR con review del owner del área correspondiente.
- **Cambios de estilo** (typos, ejemplos, formato):
  - PR con review simple.

## Convenciones de los documentos

- **Markdown estándar** + diagramas Mermaid.
- **Tablas** preferidas a listas para info estructurada.
- **Insights/notas** se enmarcan con el patrón:
  > **Importante:** ...
- **Decisiones arquitectónicas** documentadas con justificación + alternativas consideradas.
- **Anti-patrones** explícitamente listados — qué NO hacer es tan importante como qué hacer.

## Si encuentras un error

PR directo. La documentación es código de plataforma — se versiona como código.
