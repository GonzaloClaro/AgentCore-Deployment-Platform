# Plan de Implementación Incremental

> **Principio rector:** entregar valor desde la Fase 1 con el caso más simple, y agregar capacidades solo cuando aparezca dolor real. **Construir todo de golpe es la principal causa de muerte temprana de plataformas internas.**

## Filosofía de fasing

- **Cada fase deja un sistema funcional**, no un esqueleto. Un equipo puede pausar entre fases sin que la plataforma quede inservible.
- **Cada fase agrega 1-2 capacidades nuevas**, no 10. Pequeñas iteraciones, retrospectiva al final, ajuste antes de seguir.
- **Las capacidades avanzadas son OPT-IN.** El sistema funciona sin Cedar policies, sin runtime_iam custom, sin telemetry, sin sharding. Si no se declara → comportamiento default razonable.
- **Disparador (trigger) explícito por fase.** No avanzar sin que aparezca el dolor o la necesidad de la fase siguiente.

## Las fases son acumulativas

Cada fase requiere lo de la anterior. **NO se puede skipear** una fase intermedia. Si quieres llegar a Cedar policies (Fase 6), tienes que pasar por las 5 anteriores.

---

## Fase 0 — Foundations (semanas 1-2)

**Objetivo:** la cuenta DEV existe, GitLab tiene los repos, el pipeline puede comunicarse con AWS. Aún no hay agentes desplegados.

### Scope
- 3 cuentas AWS aprovisionadas (`dev-agentcore`, `qa-agentcore`, `prd-agentcore`).
- Roles IAM `deployer` con OIDC trust hacia GitLab.
- 8 repos GitLab creados con permisos básicos.
- Variables CI/CD configuradas según `CI_VARIABLES.md` (al menos para DEV).
- `foundation/bootstrap/` aplicado en cuenta DEV: KMS, S3 artifact buckets, IAM roles base.

### NO se incluye
- Default gateways (no necesarios sin tools/MCP).
- VPC endpoints (postergar a Fase 4 si runtime corre en VPC).
- Drift detection scheduled.

### Entregable
- Pipeline puede conectarse a AWS DEV y crear un bucket S3 de prueba.
- `aws sts get-caller-identity` desde un job CI muestra el role correcto.

### Criterio de éxito
✅ Un dev de plataforma puede correr `terraform apply` en `foundation/bootstrap` desde el pipeline DEV sin errores.

---

## Fase 1 — Hello World (semanas 3-4)

**Objetivo:** desplegar 1 agente trivial end-to-end en DEV. **El primer momento "wow".**

### Scope
- Componentes CI mínimos publicados con tag `v0.1.0`:
  - `validate_manifest`, `package_artifact`, `build_image`, `render_tfvars`, `trigger_iac`, `smoke_test`
- Composition `agent-base` (runtime + observability básico, sin memory).
- Pipeline `pipeline_deploy_agents_minimal.yml` (la versión reducida) en Compose.
- 1 workload `agents/sandbox/hello-world/`:
  - `manifest.yaml` con `composition: agent-base`
  - `src/agent.py` con FastAPI mínimo (echo "hello")
  - Sin prompts, sin KB, sin tools, sin Cedar, sin runtime_iam, sin models declarados (hardcodea Claude 3.5 Sonnet temporalmente — ese hardcode es deuda técnica que se paga en Fase 3).

### NO se incluye
- `agent-chatbot` ni otras compositions (sin memory todavía).
- Knowledge Bases.
- Cedar policies.
- Tests pytest del CI components (deuda técnica aceptada para acelerar primer deploy).

### Entregable
```bash
# Push a branch dev en AgentPlatform
git push origin dev

# Pipeline corre, crea ECR repo, builda imagen ARM64, despliega runtime,
# smoke test invoca /ping y responde 200.
aws bedrock-agentcore invoke-agent-runtime \
    --agent-runtime-arn arn:aws:bedrock-agentcore:us-east-1:...:agent-runtime/hello-world-dev/live \
    --payload '{"prompt":"hi"}'
# → {"role":"assistant","content":"hello: hi"}
```

### Criterio de éxito
✅ Tiempo desde `git push` a smoke OK < 12 minutos.
✅ Un dev junior puede subir un nuevo agente trivial siguiendo `_template/` en < 2 horas.

### Disparador para Fase 2
Aparece el segundo equipo queriendo desplegar su agente.

---

## Fase 2 — Multi-team handoff (semanas 5-6)

**Objetivo:** múltiples comunidades usan la plataforma sin conflictos.

### Scope
- Composition `agent-chatbot` (runtime + memory + observability).
- Componente `scan_image` (Trivy/Inspector con gate por severity HIGH).
- Componente `validate_structure` (validación cruzada en stage `validate`).
- Tests pytest del CI components (mínimo: validate_structure, render_tfvars).
- Pipeline `pipeline_infra_tests.yml` con `terraform validate` + `terraform fmt`.
- Pre-commit hooks documentados en `_template/`.
- Manual approval gate en QA: pipeline corre hasta plan, requiere click humano para apply.

### NO se incluye
- Cedar policies.
- Runtime IAM custom.
- Modelos declarativos (sigue hardcodeado).
- Telemetría a CloudWatch (logs en GitLab UI siguen siendo el único canal).

### Entregable
- 3+ workloads de equipos distintos desplegados en DEV.
- 1 promovido a QA con approval manual.
- Tests CI corren en cada MR de Componentes-AgentCore.

### Criterio de éxito
✅ Un equipo nuevo puede desplegar su agente sin pedir ayuda al equipo de plataforma.
✅ Un PR con typo en el manifest se detecta en stage `validate` (validate_structure) en < 1 minuto.

### Disparador para Fase 3
Aparece la primera petición de RAG (caso "necesito que el agente lea estos PDFs").

---

## Fase 3 — RAG y Prompts versionados (semanas 7-9)

**Objetivo:** agentes con conocimiento curado y prompts auditables.

### Scope
- Composition `agent-with-kb` (+ knowledge-base module).
- Componente `publish_prompt` (SDK → Bedrock Prompt Management).
- Modelos declarativos: `spec.models[]` en el manifest, `allowed_models.yml` con whitelist organizacional, `validate_structure` ampliado.
- `_template/src/agent.py` actualizado con helper `model_config(alias)` (ya no hardcoded).
- Componente `apply_policy` agregado (aún sin Cedar real, pero el plumbing existe).

### NO se incluye
- Multi-account sharding.
- Lifecycle protection PRD (aún todo va a 1 cuenta DEV/QA).
- Drift detection.

### Entregable
- 1 agente con KB de S3 y prompts versionados en Bedrock Prompt Mgmt.
- Cambio de modelo (Sonnet → Haiku) demostrable solo con MR al manifest.

### Criterio de éxito
✅ Cambiar de modelo NO requiere modificar código Python del agente.
✅ Un equipo de prompt engineering puede iterar prompts sin involucrar al equipo de plataforma.

### Disparador para Fase 4
Compliance/seguridad pide poder bloquear el deploy en PRD por cambios destructivos.

---

## Fase 4 — Promoción a PRD con gates (semanas 10-12)

**Objetivo:** los agentes ya pueden vivir en PRD con compliance y seguridad apropiados.

### Scope
- `foundation/bootstrap` aplicado en QA y PRD.
- `foundation/default-gateways` aplicado (los 3 gateways: 3LO, 2LO, SigV4) — incluso si aún no hay tools que los usen.
- Lifecycle protection PRD: IAM Deny en deployer role + emergency destroyer role + manual gate destroy.
- Pipeline `pipeline_infra.yml` con `prd-destroy-acknowledge` gate.
- `RUNBOOK_DESTROY_PRD.md` validado por compliance.
- Branches dev/qa/main con políticas de protección en GitLab.
- Tags semver `vX.Y.Z` para releases de Infra-AgentCore.

### NO se incluye
- Tools (gateway-target sigue sin usarse).
- Cedar policies.
- Multi-account sharding (aún 1 cuenta PRD).

### Entregable
- 2-3 agentes en PRD con tráfico real.
- Manual approval funcional para QA y PRD.
- Auditoría puede preguntar "qué cambió en PRD el último mes" y la respuesta sale del git log.

### Criterio de éxito
✅ Un compliance officer puede revertir un deploy de PRD via MR sin involucrar al equipo de plataforma.
✅ Intentar `terraform destroy` desde el pipeline PRD falla con mensaje claro.

### Disparador para Fase 5
Aparece el primer caso que requiere tools externas (HTTP API, Lambda).

---

## Fase 5 — Tools, MCP y gateway targets (semanas 13-16)

**Objetivo:** agentes pueden invocar herramientas externas y MCP servers.

### Scope
- Composition `agent-with-tools` (runtime + memory + gateway-target en gateway por defecto).
- Composition `mcp-server` (runtime + oauth provider + gateway-target).
- Composition `tool-lambda` (Lambda + gateway-target).
- Componente `upload_secret` (CI var → Secrets Manager con KMS).
- Componente `deploy_tool` (macro).
- Tools template (`tools/_template_embedded`, `tools/_template_lambda`).
- Schema actualizado con `spec.gateway_targets`, `spec.tool`, `spec.oauth_provider`.

### NO se incluye
- Cedar policies (Fase 6).
- Sharding (Fase 7).
- Runtime IAM custom (puede entrar aquí o en Fase 6 según necesidad).

### Entregable
- 1 MCP server desplegado y registrado en gateway `oauth-3lo`.
- 1 agente que invoca una Lambda tool a través del gateway.

### Criterio de éxito
✅ Un dev puede convertir su tool de "embedded" a "lambda" cambiando `tool.kind` y `composition` en el manifest.
✅ El gateway `oauth-3lo` rechaza requests sin JWT válido.

### Disparador para Fase 6
Compliance pide control fine-grained sobre qué usuarios pueden invocar qué tools.

---

## Fase 6 — Cedar policies y runtime IAM custom (semanas 17-19)

**Objetivo:** autorización fine-grained y permisos AWS específicos por workload.

### Scope
- Módulo `gateway-policy` con `local-exec` (CLI `agentcore`).
- Componente `apply_policy` ya integrado y produciendo `cedar_policies.json`.
- Módulo `runtime-role` con managed_policy_arns + inline_policies.
- Composiciones de agente actualizadas con `runtime_role.tf` y `gateway_policies.tf` opcionales.
- IAM Deny PRD ya activo (de Fase 4) ahora protege contra runtime_iam mal configurado.
- Cedar policies en modo `LOGONLY` para piloto, promoción a `ENFORCE` cuando logs lo justifiquen.
- Tests pytest cubriendo runtime_iam y gateway_policies.

### NO se incluye
- Sharding (todavía 1 cuenta PRD).

### Entregable
- 1 agente con `runtime_iam.managed_policy_arns` apuntando a managed policy creada por equipo de accesos.
- 1 agente con Cedar policies en LOGONLY → 2 semanas de soak → promoción a ENFORCE con MR.

### Criterio de éxito
✅ Equipo de accesos crea managed policies que devs solo referencian por ARN (no editan).
✅ Compliance officer puede listar políticas Cedar activas con `agentcore status`.

### Disparador para Fase 7
Una sola cuenta PRD se queda corta de quotas (>60% de runtimes/cuenta usados).

---

## Fase 7 — Multi-account sharding (semanas 20-24)

**Objetivo:** escalar horizontalmente cuando una cuenta PRD se llena.

### Scope
- Cuenta `prd-agentcore-shard-b` aprovisionada (Control Tower).
- Deployable `iac/AgentCore/agentcore-prd-shard-b` clonado del existente.
- Schema con `metadata.target_shard` ya está, ahora se usa.
- `render_tfvars` y `trigger_iac` propagan `TARGET_IAC_PROJECT` correctamente al shard.
- `MULTI_ACCOUNT.md` validado con 1 migración real (un workload movido de shard-a a shard-b).
- Capacity planning dashboard (manual al inicio, automatizado en Fase 8).

### NO se incluye
- Federación cross-shard (un agente en shard-a llamando a tool en shard-b).
- Multi-tenant per business unit (eso es Fase 9+).

### Entregable
- 2 cuentas PRD activas con workloads distribuidos por capability.
- Diagrama actualizado de la plataforma con N shards.

### Criterio de éxito
✅ Crear shard nuevo (cuenta + deployable) toma < 1 día.
✅ Migrar workload de un shard a otro toma < 1 día (con MR + ventana de mantenimiento).

### Disparador para Fase 8
La cantidad de pipelines diarios hace que GitLab UI ya no sea suficiente para troubleshooting.

---

## Fase 8 — Observabilidad completa y SRE (semanas 25-28)

**Objetivo:** SRE puede operar la plataforma sin necesitar entender los detalles internos.

### Scope
- Componente `pipeline_telemetry` integrado en pipelines (TRACE_ID cross-pipeline a CloudWatch).
- Componente `drift_check` + pipeline `pipeline_drift_detection.yml` scheduled nightly.
- Dashboard CloudWatch correlacionando TRACE_ID con métricas Bedrock (invocations, latency, errors).
- Alertas SNS conectadas al canal del equipo SRE (PagerDuty / Slack / Teams).
- Runbooks documentados por categoría de error (build failed, scan failed, plan failed, apply failed).
- Cost tracking automático por capability/owner (basado en tags AWS).

### NO se incluye
- Federation cross-tenant.
- AI descentralizada full.

### Entregable
- Dashboard único "estado de la plataforma" con todos los pipelines del día.
- SRE puede dar root cause analysis de cualquier falla de pipeline en < 5 minutos buscando TRACE_ID.

### Criterio de éxito
✅ MTTR (Mean Time To Recovery) de pipeline failures < 30 minutos.
✅ Drift detection captura > 95% de drifts antes de que un humano los reporte.

### Disparador para Fase 9
Onboarding de un nuevo dev junior toma > 1 semana → la plataforma necesita ergonomía.

---

## Fase 9 — Developer experience completo (semanas 29-32)

**Objetivo:** la plataforma se siente como un producto, no como una pieza de infra.

### Scope
- `agentcore-cli` local con comandos: `new`, `validate`, `preview`, `deploy-local`, `logs`, `status`.
- Codegen del JSON-schema → docs Markdown automáticas.
- Renovate/Dependabot integrado.
- Documentación interactiva (Backstage o mkdocs hosted).
- Snippets IDE (VSCode + JetBrains).
- "Starter kit" template repository con 1 agente working out-of-the-box.

### Entregable
- Onboarding de dev nuevo: clonar starter, correr `agentcore-cli new`, push → deploy. < 30 minutos.

### Criterio de éxito
✅ Promotores Net Score (NPS) interno de la plataforma > 40.
✅ % de PRs aprobados sin pedir cambios al manifest > 80%.

---

## Fase 10+ — Federación e IA descentralizada (no prescriptiva)

A partir de aquí el roadmap depende de cómo evoluciona la organización. Posibles direcciones (no excluyentes):

- **Multi-tenant por business unit:** cada unidad tiene su propia cuenta AgentCore, con federación de gateways central.
- **Cross-shard agent invocation:** agentes hablando entre cuentas via A2A protocol.
- **Marketplace interno de agentes y tools:** registry centralizado con descubrimiento.
- **Plataforma como producto externo:** ofrecer la plataforma a partners o tenants externos.

Cada uno requiere ~1 quarter de exploración + 1-2 quarters de implementación.

---

## Tabla resumen

| Fase | Duración | Capacidad agregada | Workloads esperados al final |
|---|---|---|---|
| 0 | 2 sem | Foundations | 0 |
| 1 | 2 sem | Hello world | 1 |
| 2 | 2 sem | Multi-team | 3-5 |
| 3 | 3 sem | RAG + prompts versionados + modelos declarativos | 5-10 |
| 4 | 3 sem | PRD con gates | 5-10 (3-5 en PRD) |
| 5 | 4 sem | Tools + MCP | 10-20 |
| 6 | 3 sem | Cedar + IAM custom | 15-25 |
| 7 | 5 sem | Multi-account sharding | 30-50 |
| 8 | 4 sem | Observabilidad SRE | 50-100 |
| 9 | 4 sem | Developer experience | 100-200 |
| 10+ | ongoing | Federación / descentralización | 200+ |

**Tiempo total a 100+ workloads en PRD:** ~32 semanas (~8 meses) con 1 equipo de plataforma dedicado.

## Reglas de transición entre fases

- **Retrospectiva al final de cada fase** con stakeholders consumidores (CoE de IA, equipos comunidades).
- **Las decisiones de la fase siguiente se toman al inicio de esa fase**, no al inicio del proyecto. Las prioridades cambian con la realidad.
- **Skipear capacidades no disparadas.** Si en Fase 6 no hay caso real para Cedar, postergarlo hasta que aparezca.
- **Documentar la deuda técnica aceptada** explícitamente en cada fase (ej: "Fase 1 acepta hardcoded model_id").
