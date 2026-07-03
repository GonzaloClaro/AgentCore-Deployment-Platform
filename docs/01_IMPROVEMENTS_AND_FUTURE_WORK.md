# Mejoras y Trabajo Futuro

> Inventario vivo de lo que falta y de lo que mejoraría el framework. Priorizar según fase y dolor real, no antes.

## Categorías

1. [Robustez operacional](#1-robustez-operacional)
2. [Developer experience](#2-developer-experience)
3. [Funcionalidades de plataforma](#3-funcionalidades-de-plataforma)
4. [Gobernanza y observabilidad](#4-gobernanza-y-observabilidad)
5. [Optimización y costos](#5-optimización-y-costos)
6. [Federación y descentralización](#6-federación-y-descentralización)
7. [Compliance y regulación](#7-compliance-y-regulación)
8. [Integración con sistemas corporativos](#8-integración-con-sistemas-corporativos)
9. [Testing end-to-end y validación real](#9-testing-end-to-end-y-validación-real)
10. [Operación SRE y respuesta a incidentes](#10-operación-sre-y-respuesta-a-incidentes)

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
| 1.8 | Recovery runbooks para escenarios específicos: gateway saturado, KB out-of-sync, secret comprometido, model drift, runtime caído | Hoy solo existe runbook de destroy. Cada modo de falla necesita su procedimiento documentado | Medio | Antes del primer agente productivo |
| 1.9 | Drift detection real corriendo diariamente con alertas | Hoy mencionado en doc, no implementado. Entornos productivos divergen del state si alguien toca por consola | Medio | Pre-PRD del primer agente |

## 2. Developer experience

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 2.1 | `agentcore-cli` local | El más importante: `agentcore new agent-chatbot`, `agentcore validate`, `agentcore preview-tfvars` | Alto | Cuando onboarding pase de 1 dev a >5 |
| 2.2 | Pre-commit hooks: yamllint, terraform fmt, JSON-schema check del manifest | Errores detectados en local en lugar de CI | Bajo | Inmediato cuando haya >3 contributores |
| 2.3 | Renovate/Dependabot para versiones provider AWS Terraform | AgentCore evoluciona rápido (issues #46128, #45099 ya prueban esto) | Bajo | Cuando se despliega a PRD |
| 2.4 | Codegen schema → docs Markdown automáticas | Cambios al JSON-schema actualicen MANIFEST_REFERENCE.md y _template/manifest.yaml automáticamente | Medio | Cuando haya 2 cambios al schema sin propagar |
| 2.5 | Validador local del manifest (sin pipeline) | Dev edita manifest, ejecuta `agentcore validate` localmente, ve errores en 2 segundos | Bajo (parte del CLI) | Junto al CLI |
| 2.6 | Templates de IDE (VSCode snippets, JetBrains live templates) para manifest.yaml | Productividad al escribir manifests nuevos | Bajo | Junto al CLI |
| 2.7 | Documentación interactiva (Backstage, mkdocs, hosted) | Equipos consumidores leen docs de plataforma como si fuera producto | Medio-Alto | Pre-Fase 5 |
| 2.8 | Loop de desarrollo local del Python de los componentes | Hoy un dev que toca render_tfvars debe pushear y esperar el CI. Falta poder ejecutar componentes con fixtures locales | Medio | Cuando haya >2 contribuidores en Componentes-AgentCore |
| 2.9 | Decision tree "qué composition usar" como árbol interactivo | Hoy el dev debe leer todo MANIFEST_REFERENCE para decidir entre agent-chatbot vs agent-with-tools vs agent-with-kb | Bajo | Junto a la documentación interactiva |

## 3. Funcionalidades de plataforma

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 3.1 | Composiciones adicionales según demanda (no por adelantado) | "Crear nueva composition copiando la más cercana" es buen patrón, pero algunas se materializarán | Variable | Cuando 3+ workloads pidan lo mismo |
| 3.2 | Soporte de **inference profile auto-resolution** | Mapear `model_id: claude-3-5-sonnet` → ARN del inference profile correcto sin que el dev lo escriba | Medio | Cuando >5 workloads usen cross-region |
| 3.3 | Soporte de **AgentCore Browser** y **Code Interpreter** como módulos TF + componentes CI | Casos de uso de automatización conversacional o web los pedirán | Alto | Cuando 1er use case real lo pida |
| 3.4 | ~~Soporte de **A2A protocol**~~ Auto-discovery de ARN entre agentes (A2A) | Modo manual ya soportado: `spec.runtime.server_protocol: A2A` + ARN del agente-persona a mano en `runtime.env` (ver MANIFEST_REFERENCE.md §2.4.bis). Falta: publicar/descubrir ARNs automáticamente (SSM Parameter Store o `terraform_remote_state`) para no depender de copy-paste manual | Medio | Cuando el copy-paste manual de ARNs entre 3+ agentes se vuelva doloroso |
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
| 4.8 | Clasificación de datos en el manifest (`spec.data_classification`) | Declarar si el agente toca PII, datos sensibles, públicos. Define qué cuenta/red puede correrlo | Bajo (campo) + Medio (enforcement) | Cuando exista política corporativa de clasificación |
| 4.9 | Audit trail inmutable con retention configurable | Eventos de pipeline (quién aprobó, qué versión, cuándo) en almacenamiento WORM con retention legal | Medio | Cuando aplique exigencia regulatoria |

## 5. Optimización y costos

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 5.1 | Compartir KBs entre agentes (cross-workload references) | Hoy cada agente con KB crea su propia. Una KB shared con readers puede ahorrar costo | Medio | Cuando 3+ agentes pidan misma KB |
| 5.2 | Lifecycle policies S3 más finas | Hoy tienen reglas básicas. Por capability podrían ser más agresivas | Bajo | Cuando S3 storage cost > umbral |
| 5.3 | Lambda layers compartidas para tools embedded comunes | Reusar boto3 + libs estándar entre tools | Bajo | Cuando >10 lambdas tools desplegadas |
| 5.4 | Modelo "preview" en dev: imágenes runtime más livianas | Optimizar tiempo de cold start en dev | Bajo | Cuando devs reporten tiempo de feedback alto |

## 6. Federación y descentralización

> Esta categoría es el camino hacia **AI descentralizada**: cuentas por unidad organizacional, federación de gateways, plataforma multi-tenant.

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 6.1 | Cross-shard agent invocation | Un agente en `prd-shard-a` llama a un MCP en `prd-shard-b` | Alto | Cuando aparezca caso de negocio |
| 6.2 | Gateway federation (un gateway viendo targets de múltiples cuentas) | Tools compartidas entre tenants sin duplicar | Alto | Cuando haya >3 tenants |
| 6.3 | Tenant isolation a nivel de cuenta (modelo Control Tower) | Cada unidad organizacional tiene su cuenta AgentCore propia | Muy alto | Cuando estructura organizacional lo permita |
| 6.4 | Cross-account registry de agentes | Equipo A descubre y reusa agentes de equipo B sin duplicar | Alto | Junto a 6.3 |
| 6.5 | Plataforma multi-tenant con quotas por tenant | Soft-quotas por unidad organizacional dentro de un mismo shard | Medio | Cuando haya conflictos de quota entre teams |
| 6.6 | Whitelist de modelos por tenant (no solo por ambiente) | Tenant X solo puede usar modelos aprobados por su unidad | Bajo | Cuando haya regulación tenant-specific |

## 7. Compliance y regulación

> Categoría crítica para empresas grandes con requisitos regulatorios estrictos. Cada item suele requerir aprobación de un equipo legal o de compliance interno antes de productivizarse.

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 7.1 | Separation of Duties enforcement: committer ≠ approver del MR | Hoy hay manual approval pero nada impide que el mismo usuario haga ambos | Bajo | Pre-PRD primer agente |
| 7.2 | SBOM (Software Bill of Materials) firmado por imagen | Generar y firmar SBOM con cosign / sigstore. Requerido por supply chain security en industrias reguladas | Medio | Cuando exista política de supply chain |
| 7.3 | Encryption-at-rest con HSM-backed keys (FIPS 140-2 Level 3) | KMS con custom key store apuntando a CloudHSM. Alguna jurisdicción lo exige para datos sensibles | Alto | Cuando aplique requisito FIPS o equivalente |
| 7.4 | Definición de RTO/RPO por composition | Cada arquetipo de workload necesita objetivo de recovery. agent-chatbot RTO=15min, mcp-server RTO=1h, etc. | Medio | Pre-PRD del primer agente |
| 7.5 | DR drills programados | Simulacros trimestrales de pérdida de cuenta/región. Sin drill, el plan de DR está sin validar | Medio (drill) + Alto (automatización) | Anual / cuando el negocio exija evidencia de DR |
| 7.6 | Multi-región con failover automático | Hoy el código asume `us-east-1`. Plataforma productiva en industrias críticas exige al menos active-passive entre regiones | Muy alto | Cuando aparezca exigencia de availability >99.95% |
| 7.7 | Data residency enforcement | El manifest declara región permitida; la plataforma rechaza despliegue fuera de esa región | Bajo (validación) + Medio (enforcement) | Cuando exista regulación de residencia de datos |
| 7.8 | Retention policy granular en logs y artefactos | Hoy hay lifecycle básico en S3. Industrias reguladas exigen retention de 7-10 años con WORM (Object Lock) | Medio | Cuando aplique exigencia regulatoria |
| 7.9 | Vulnerability management policy automatizada | Política que falla pipeline si hay CVE crítico sin parchear N días, no solo HIGH+ en scan_image | Bajo | Cuando exista política corporativa de SLA de parches |
| 7.10 | Política de rotación de secretos automática | Hoy `upload_secret` sube y olvida. Industrias reguladas exigen rotación cada 90 días con auditoría | Medio | Cuando aplique exigencia regulatoria |
| 7.11 | Privacy impact assessment (PIA) integrado al manifest | Si el agente toca datos personales, el manifest debe incluir referencia al PIA aprobado | Bajo | Cuando aplique GDPR / equivalente local |
| 7.12 | Secrets en plaintext durante plan: migrar a `client_secret_wo` | El módulo identity-oauth-provider lee secret de Secrets Manager y lo pasa en plano (queda en state). Migrar a write-only attributes (Terraform >= 1.11) | Bajo | Cuando se confirme Terraform >= 1.11 en runner |

## 8. Integración con sistemas corporativos

> Categoría que en empresas grandes representa el **40-60% del esfuerzo total** del proyecto. Cada integración suele ser un proyecto en sí mismo con su propio timeline y aprobaciones.

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 8.1 | IdP corporativo (Okta / Azure AD / SAML / OIDC) | Hoy hay placeholder de OIDC discovery pero ninguna integración real con IdP corporativo. Define quién puede invocar agentes | Alto | Pre-PRD primer agente |
| 8.2 | Network corporativo (Direct Connect, Transit Gateway, peering on-prem) | VPC endpoints es buen comienzo. Integración con red corporativa es un proyecto del equipo de redes | Muy alto | Cuando haya tráfico desde on-prem |
| 8.3 | SIEM corporativo (Splunk, Sentinel, Elastic) | Logs CloudWatch deben replicarse al SIEM para correlación con eventos del resto de la organización | Medio | Pre-PRD primer agente |
| 8.4 | ITSM (ServiceNow, Jira Service Management, BMC Remedy) | Cambios productivos abren un Change Request automáticamente. Approval gate consulta status del CR | Medio | Cuando exista política de change management |
| 8.5 | SCA / SAST corporativo (Veracode, Black Duck, Snyk Enterprise) | Hoy `scan_image` usa Trivy. Política corporativa puede exigir herramienta específica con licencia paga | Bajo (integración) | Cuando exista política corporativa SCA |
| 8.6 | Cost allocation tags + showback/chargeback a FinOps | Tags obligatorios (`CostCenter`, `BusinessUnit`, `Owner`) propagados desde manifest hasta cada recurso AWS | Bajo (tags) + Medio (reportes) | Cuando FinOps lo exija |
| 8.7 | Naming conventions corporativas | Hoy nombres son `agentcore-{env}-...`. Convención corporativa puede exigir prefijo de unidad organizacional, código de proyecto, etc. | Bajo | Pre-bootstrap de primera cuenta corporativa |
| 8.8 | Identity federation runtime → APIs corporativas | Agente necesita llamar a un API interno con OAuth corporativo. Workload identity de AgentCore + token exchange con IdP corporativo | Alto | Cuando aparezca primer agente que llama a API interna |
| 8.9 | Service catalog corporativo (Backstage, Port, Cortex) | Manifests publican metadata al catálogo corporativo además de a LeanIX | Medio | Cuando exista catálogo corporativo |
| 8.10 | Code review gates corporativos (CODEOWNERS por path, required reviewers) | GitLab CODEOWNERS apuntando a equipos según path; arquitectura aprueba modules, plataforma aprueba foundation | Bajo | Cuando haya >2 equipos contribuyendo |
| 8.11 | Approval workflow integrado (no solo manual approval de GitLab) | Workflow de aprobación con CAB / Change Manager / Product Owner según severidad del cambio | Medio | Cuando exista política de gobierno de cambios |

## 9. Testing end-to-end y validación real

> Hoy el código pasa `terraform validate` (chequeo de schema). Eso no es lo mismo que **funciona en una cuenta AWS real**. Esta categoría cierra la brecha.

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 9.1 | `scripts/tf-plan-local.sh` que simule el flujo CI con manifest fixture | Permite ejecutar `terraform plan -refresh=false` localmente con un manifest de ejemplo. Detecta errores que `validate` no captura | Bajo | Inmediato (próximo paso después del actual estado del repo) |
| 9.2 | Terratest end-to-end por composition | Para cada composition: deploy a sandbox, verificación de recursos creados, destroy. Corre en CI nightly | Alto | Antes de 5 agentes en PRD |
| 9.3 | Primer agente real desplegado en cuenta sandbox | Validación más importante. Descubre todo lo que está oculto: red corporativa, IAM corporativa, naming, herramientas obligatorias | Medio (depende del entorno) | Hito crítico de validación de la plataforma |
| 9.4 | Smoke test extendido (no solo `/ping`) | Invocación real del agente con prompt fijture, verificar que el modelo responde, las tools se invocan, el KB devuelve documentos | Medio | Junto al primer agente real |
| 9.5 | Chaos engineering / fault injection | AWS Fault Injection Simulator para probar comportamiento cuando: ECR está caído, Bedrock retorna 5xx, Memory está al máximo de quota | Alto | Pre-PRD del primer agente crítico |
| 9.6 | Performance / load testing strategy | Definir RPS objetivo por tipo de agente, herramienta de carga (Locust / k6), regresión de performance en CI | Alto | Cuando aparezca caso de uso con SLA de latencia |
| 9.7 | Tests de integración del pipeline completo (no solo unit tests) | Validar el flujo: manifest válido → render_tfvars → trigger_iac → smoke_test todo en una corrida | Medio | Pre-PRD primer agente |
| 9.8 | Validación de compatibilidad con versiones de Terraform mínimas | Si runner corporativo es Terraform 1.9, validar que el código no usa features 1.10+ | Bajo | Pre-PRD primer agente |

## 10. Operación SRE y respuesta a incidentes

> Una plataforma desplegada no es lo mismo que una plataforma operada. Esta categoría cubre lo que el equipo necesita para sostenerla 24/7.

| # | Item | Por qué importa | Esfuerzo | Disparador |
|---|---|---|---|---|
| 10.1 | SLOs definidos por composition | `agent-chatbot`: latencia p99 < 3s, error rate < 0.5%. `mcp-server`: availability > 99.5%. Sin SLOs, no hay objetivo de operación | Medio | Pre-PRD primer agente |
| 10.2 | Error budget tracking | Implementación de error budgets que pausan deploys cuando se agota el budget mensual | Medio | Cuando haya 5+ agentes con SLO definido |
| 10.3 | On-call rotation y escalation policies | Quién recibe el page cuando algo se rompe. Escalation a L2/L3 después de N minutos sin respuesta | Bajo (config) + alto (compromiso humano) | Cuando haya equipo de plataforma operativo |
| 10.4 | Runbooks ejecutables (no solo documentación) | Un runbook debe ser una secuencia de comandos copy-paste. Mejor: scripts versionados que el on-call ejecuta | Medio | Junto a SLOs |
| 10.5 | Dashboards Grafana / CloudWatch por composition | Vista única por agente con: latencia, error rate, costo, invocaciones, tokens consumidos | Medio | Cuando haya >10 agentes activos |
| 10.6 | Status page interno (público a la organización) | Equipos consumidores ven el estado de cada agente sin tener que preguntar | Medio | Cuando haya >20 agentes |
| 10.7 | Postmortem template y disciplina blameless | Después de cada incidente, postmortem en formato estándar. Sin esta disciplina, los mismos errores se repiten | Bajo (template) + alto (cultura) | Después del primer incidente real |
| 10.8 | Capacity planning con quotas Bedrock vs uso | Bedrock tiene quotas por modelo y región. Reporte semanal de uso vs cuota con proyección | Medio | Cuando alguna cuota cruce el 50% |
| 10.9 | GameDays trimestrales | Simulacro: caída de un componente crítico, equipo recupera siguiendo runbooks. Detecta runbooks desactualizados | Bajo (organización) | Trimestral cuando equipo esté formado |
| 10.10 | Capacidad de "freeze de despliegues" en eventos especiales | Botón rojo que bloquea despliegues productivos en horarios críticos del negocio | Bajo | Cuando haya eventos de calendario que lo justifiquen |

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
- ❌ Compliance teórico (sec 7) antes de tener un agente realmente desplegado (sec 9.3)
- ❌ Integraciones corporativas (sec 8) antes de coordinar con los equipos owner de esos sistemas
- ❌ SLOs aspiracionales (sec 10.1) sin baseline medido en producción

## Bloques mínimos antes de PRD

Sin estos items NO se pasa de QA a PRD:

- 1.8 (recovery runbooks)
- 1.9 (drift detection)
- 4.4 (audit log)
- 7.1 (SoD enforcement)
- 7.4 (RTO/RPO)
- 8.1 (IdP corporativo)
- 8.3 (SIEM)
- 9.3 (primer agente real desplegado)
- 9.4 (smoke test extendido)
- 10.1 (SLOs)
- 10.3 (on-call)
- 10.4 (runbooks ejecutables)

## Reseteo trimestral

Cada Q, el equipo de plataforma revisa esta lista, mueve items completados al CHANGELOG, y reordena prioridades según realidad operacional.
