# Mejoras y Trabajo Futuro

> Inventario vivo de lo que falta y de lo que mejoraría el framework. Priorizar según fase y dolor real, no antes.

## Categorías

1. [Robustez operacional](#1-robustez-operacional)
2. [Developer experience](#2-developer-experience)
3. [Funcionalidades de plataforma](#3-funcionalidades-de-plataforma)
4. [Gobernanza y observabilidad](#4-gobernanza-y-observabilidad)
5. [Optimización y costos](#5-optimización-y-costos)
6. [Federación y descentralización](#6-federación-y-descentralización)

---

## 1. Robustez operacional

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 1.1 | Tests adicionales: build_image, scan_image, upload_secret, smoke_test | Cobertura del 50% al 100% en componentes CI | Medio | Pre-PRD del primer agente |
| 1.2 | Integration tests con AWS sandbox real | Detectar regresiones que `terraform validate` no captura (la API AgentCore evoluciona rápido) | Alto | Antes de 10 agentes en PRD |
| 1.3 | Recovery runbook: state Terraform corrupto | Complemento de RUNBOOK_DESTROY_PRD | Bajo | Próximo incidente o pre-auditoría |
| 1.4 | Cleanup automático de ENI orphans (issue #45099) | Job programado que detecta y borra ENIs huérfanas tras destroys | Bajo | Cuando se vea acumulación de ENIs |
| 1.5 | Backup off-site del Terraform state | GitLab managed state + replicación a S3 secundario en cuenta de gestión | Medio | Pre-PRD o exigencia de DR |
| 1.6 | Alertas SNS conectadas a canal corporativo (PagerDuty, Slack, Teams) | Drift detection y telemetry deben llegar al canal del equipo | Bajo | Cuando haya equipo de plataforma operativo |
| 1.7 | Dashboard CloudWatch correlacionando TRACE_ID con métricas Bedrock | SRE puede ver "este pipeline → estas invocaciones del modelo → este costo" | Medio | Cuando haya >20 agentes activos |

## 2. Developer experience

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 2.1 | `agentcore-cli` local | El más importante: `agentcore new agent-chatbot`, `agentcore validate`, `agentcore preview-tfvars` | Alto | Cuando onboarding pase de 1 dev a >5 |
| 2.2 | Pre-commit hooks: yamllint, terraform fmt, JSON-schema check del manifest | Errores detectados en local en lugar de CI | Bajo | Inmediato cuando haya >3 contributores |
| 2.3 | Renovate/Dependabot para versiones provider AWS Terraform | AgentCore evoluciona rápido (issues #46128, #45099 ya prueban esto) | Bajo | Cuando se deploya a PRD |
| 2.4 | Codegen schema → docs Markdown automáticas | Cambios al JSON-schema actualicen MANIFEST_REFERENCE.md y _template/manifest.yaml automáticamente | Medio | Cuando haya 2 cambios al schema sin propagar |
| 2.5 | Validador local del manifest (sin pipeline) | Dev edita manifest, corre `agentcore validate` localmente, ve errores en 2 segundos | Bajo (parte del CLI) | Junto al CLI |
| 2.6 | Templates de IDE (VSCode snippets, JetBrains live templates) para manifest.yaml | Productividad al escribir manifests nuevos | Bajo | Junto al CLI |
| 2.7 | Documentación interactiva (Backstage, mkdocs, hosted) | Equipos consumidores leen docs de plataforma como si fuera producto | Medio-Alto | Pre-Fase 5 |

## 3. Funcionalidades de plataforma

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 3.1 | Composiciones adicionales según demanda (no por adelantado) | "Crear nueva composition copiando la más cercana" es buen patrón, pero algunas se materializarán | Variable | Cuando 3+ workloads pidan lo mismo |
| 3.2 | Soporte de **inference profile auto-resolution** | Mapear `model_id: claude-3-5-sonnet` → ARN del inference profile correcto sin que el dev lo escriba | Medio | Cuando >5 workloads usen cross-region |
| 3.3 | Soporte de **AgentCore Browser** y **Code Interpreter** como módulos TF + componentes CI | Casos de uso de banca conversacional o automatización web los van a pedir | Alto | Cuando 1er use case real lo pida |
| 3.4 | Soporte de **A2A protocol** para agentes hablando con otros agentes | AgentCore lo soporta nativo. Composition `agent-with-a2a` cuando se necesite | Alto | Cuando aparezca el primer caso multi-agente |
| 3.5 | Modelo fallback automático en helper de `agent.py` | Si el modelo PRIMARY falla, retry con FALLBACK | Bajo | Cuando un workload reporte failures |
| 3.6 | Azure API key rotation automation | Lambda + EventBridge que rota la key cada N días | Medio | Cuando haya >3 workloads Azure |
| 3.7 | Migración a recursos TF nativos cuando AWS los exponga | `aws_bedrockagentcore_policy_engine`, fix de #46128 | Bajo (cuando exista) | Vigilancia trimestral del provider |
| 3.8 | Composition `tool-openapi` (HTTP API existente registrado como gateway target) | Hoy se hace con `gateway-deploy` o `agent-with-tools`; merece composition propia | Bajo | Cuando 2+ workloads lo pidan |
| 3.9 | Soporte de **Smithy schemas** (además de OpenAPI) | Tools que vienen con Smithy ya definido | Bajo | Cuando aparezca primer caso |

## 4. Gobernanza y observabilidad

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 4.1 | LeanIX schema final | Workshop con arquitectura para definir mapping manifest → fact sheets | Medio | Pre-PRD primer agente |
| 4.2 | Cost tracking automático por workload + modelo | Bedrock emite métricas, hay que agregar dashboard + alertas FinOps | Medio | Cuando costo mensual de IA cruce umbral |
| 4.3 | A/B testing harness para comparar modelos | Útil para promoción Sonnet→Opus, etc. | Alto | Cuando exista demanda concreta |
| 4.4 | Audit log unificado: cambios de modelo, prompts, IAM policies, Cedar | Hoy está en git, pero un dashboard ayuda a auditoría externa | Medio | Cuando llegue auditoría externa |
| 4.5 | Reportes automáticos de quotas vs uso (capacity planning) | Anticipar el momento de agregar shard nuevo | Medio | Cuando haya >50 agentes en un shard |
| 4.6 | Catálogo de tools embeddable (registry interno) | Devs descubren tools existentes para reusar antes de crear nuevas | Medio | Cuando >20 tools en el ecosistema |
| 4.7 | Anomaly detection sobre métricas de invocación | Picos de error rate, latencia, costo | Alto | Cuando haya equipo SRE dedicado |

## 5. Optimización y costos

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 5.1 | Compartir KBs entre agentes (cross-workload references) | Hoy cada agente con KB crea su propia. Una KB shared con readers puede ahorrar costo | Medio | Cuando 3+ agentes pidan misma KB |
| 5.2 | Lifecycle policies S3 más finas | Hoy tienen reglas básicas. Por capability podrían ser más agresivas | Bajo | Cuando S3 storage cost > umbral |
| 5.3 | Lambda layers compartidas para tools embedded comunes | Reusar boto3 + libs estándar entre tools | Bajo | Cuando >10 lambdas tools deployadas |
| 5.4 | Modelo "preview" en dev: imágenes runtime más livianas | Optimizar tiempo de cold start en dev | Bajo | Cuando devs reporten tiempo de feedback alto |

## 6. Federación y descentralización

> Esta categoría es el camino hacia **AI descentralizada**: cuentas por business unit, federación de gateways, plataforma multi-tenant.

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 6.1 | Cross-shard agent invocation | Un agente en `prd-shard-a` llama a un MCP en `prd-shard-b` | Alto | Cuando aparezca caso de negocio |
| 6.2 | Gateway federation (un gateway viendo targets de múltiples cuentas) | Tools compartidas entre tenants sin duplicar | Alto | Cuando haya >3 tenants |
| 6.3 | Tenant isolation a nivel de cuenta (modelo Control Tower) | Cada business unit tiene su cuenta AgentCore propia | Muy alto | Cuando estructura organizacional lo permita |
| 6.4 | Cross-account registry de agentes | Equipo A descubre y reusa agentes de equipo B sin duplicar | Alto | Junto a 6.3 |
| 6.5 | Plataforma multi-tenant con quotas por tenant | Soft-quotas por business unit dentro de un mismo shard | Medio | Cuando haya conflictos de quota entre teams |
| 6.6 | Whitelist de modelos por tenant (no solo por ambiente) | Tenant X solo puede usar modelos aprobados por su BU | Bajo | Cuando haya regulación tenant-specific |

---

## Cómo priorizar

**Regla mental:** un item de esta lista solo se ejecuta cuando se cumple su disparador. Construir antes = waste.

**Score sugerido por item:**
```
score = (impacto_si_falta) × (probabilidad_de_dolor) / esfuerzo
```

- `impacto_si_falta`: 1-5 (1=cosmético, 5=blocker)
- `probabilidad_de_dolor`: 0-1 según trigger
- `esfuerzo`: 1-5 días equivalentes

**Items >score 4** entran al backlog del sprint próximo del equipo de plataforma.

## Anti-patrones de roadmap

- ❌ Implementar todo el catálogo "por si acaso"
- ❌ Adoptar features de AgentCore que aún están en preview en producción
- ❌ Construir el `agentcore-cli` antes de validar el flujo manual con 5+ devs reales
- ❌ Federación cross-account antes de tener 1 cuenta funcionando bien
- ❌ Dashboard de costo antes de tener facturación que justifique mirarlo

## Reseteo trimestral

Cada Q, el equipo de plataforma revisa esta lista, mueve items completados al CHANGELOG, y reordena prioridades según realidad operacional.
