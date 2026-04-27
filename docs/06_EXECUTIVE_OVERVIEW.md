# Visión Ejecutiva — Plataforma AgentCore como producto interno

> **Audiencia:** Gerencia, dirección de tecnología, sponsors. **Objetivo:** explicar por qué este enfoque es el correcto para una organización grande y compleja que va a desplegar cientos de agentes IA, qué compromisos requiere de cada área, y cómo se proyecta hacia un futuro descentralizado.

---

## 1. El problema que resolvemos

Las organizaciones grandes con cientos de colaboradores enfrentan tres tensiones simultáneas cuando empiezan a producir agentes IA a escala:

| Tensión | Manifestación |
|---|---|
| **Velocidad vs Gobernanza** | Los equipos quieren desplegar rápido. Compliance/Seguridad quiere control. Sin plataforma, ganan los más ruidosos y pierde la consistencia. |
| **Aislamiento vs Reutilización** | Cada equipo arma su pipeline, su Terraform, su forma de hacer prompts. Se duplica trabajo y se fragmenta el catálogo. |
| **Innovación vs Compliance regulatorio** | Industrias reguladas exigen audit trail, rotación de secretos, separación de roles. Fricciona con la velocidad de iteración natural de IA. |

El resultado típico sin plataforma: **3 meses para desplegar el primer agente, 9 meses para que el segundo equipo lo replique, 18 meses para que la organización tenga una práctica consolidada — y para entonces el ecosistema interno ya tiene 5 formas distintas de hacer lo mismo, 0 reutilización, y compliance reportes manuales.**

## 2. La propuesta: Plataforma como Producto Interno

Tratamos la plataforma de despliegue de agentes como un **producto interno con consumidores definidos**. No es un proyecto que se entrega y se olvida — es una capacidad continua que evoluciona con la demanda.

### Principios de diseño

1. **Self-service para los equipos consumidores.** Un equipo de un dominio funcional escribe un manifest declarativo + código de su agente, hace `git push`, y la plataforma lo despliega sin necesitar tickets a otros equipos.
2. **Gobierno fuerte sin sacrificar velocidad sostenida.** Compliance, seguridad y FinOps quedan codificados como guardrails (whitelists, manual gates, IAM denies). Los equipos no los esquivan porque están integrados al flujo natural.
3. **Descomposición por responsabilidad.** Cada artefacto del agente (modelo, prompt, KB, IAM, tools) es un eje de cambio independiente con su propio ciclo de vida. Cambiar un prompt no requiere reaprobar el agente entero.
4. **Multi-cuenta desde día 1, multi-tenant cuando aparezca el dolor.** El framework soporta sharding horizontal (más cuentas por ambiente) que habilita transición eventual a esquema descentralizado.
5. **Plataforma como código.** Todo es revisable: pipelines, módulos Terraform, schemas, whitelists, permisos. Audit trail = git log.

### Por qué este enfoque y no otros

| Alternativa | Por qué no |
|---|---|
| **Terraform crudo en cada repo** | Cada equipo reinventa, sin governance, fragmentación de prácticas. |
| **CDK / framework imperativo** | Mismo problema de gobernanza; además `plan/apply` deja de ser declarativo y revisable. |
| **SaaS de terceros** | No personalizable a la regulación específica. Vendor lock-in. Latencia de feature requests. |
| **Plataforma propia sin abstracción declarativa** | Los devs siguen escribiendo Terraform → barrera de entrada alta → pocos equipos adoptan. |
| **Generación dinámica de HCL desde manifests** | `terraform plan` deja de ser revisable, audit no funciona. |

El enfoque de **manifest opinado + composiciones predefinidas con flags + plataforma como producto** balancea las 5 tensiones mejor que cualquier alternativa que se haya considerado.

---

## 3. Compromisos requeridos por área

Esta plataforma **NO es viable** sin compromisos formales de las siguientes áreas. Cada compromiso es un input necesario, no un nice-to-have.

### 3.1 DevOps (CI/CD + GitLab)

**Compromiso:**
- Operar y mantener GitLab (servidor, runners, escalado).
- Proveer **runners ARM64** (o emulación QEMU) para builds de imágenes.
- Mantener templates organizacionales de runners y políticas de seguridad de GitLab.
- Acompañar versionado y release de los repos `Componentes-AgentCore` y `Compose-AgentCore`.
- Configurar CI/CD variables a nivel group/project según `CI_VARIABLES.md`.

**Métrica de servicio:**
- Disponibilidad de runners > 99.5%.
- Latencia de pipeline (sin queue) < 30 segundos para iniciar.

### 3.2 CloudOps (Infraestructura + Terraform)

**Compromiso:**
- Provisionar las 3 cuentas AWS iniciales y N cuentas adicionales para sharding.
- Account Factory / Control Tower configurado para clonar cuentas con baseline.
- Operar y mantener `foundation/bootstrap`, `foundation/default-gateways`, `foundation/vpc-endpoints` por cuenta.
- VPCs, subnets, KMS keys y Transit Gateway según patrones corporativos.
- Coordinar quota increases con AWS Support cuando sean necesarios.
- Mantener pin de versión del provider AWS Terraform.

**Métrica de servicio:**
- Tiempo para provisionar una shard nueva (cuenta + foundation aplicado) < 1 día.
- Tiempo de respuesta a quota increase request < 3 días.

### 3.3 Equipo de Accesos (IAM + Identity Providers)

**Compromiso:**
- Crear y mantener **managed policies aprobadas** que los devs referencian por ARN (`runtime_iam.managed_policy_arns`).
- Documentar el catálogo de managed policies disponibles y para qué se usan.
- Configurar y mantener los **Identity Providers OAuth** corporativos (issuers, discovery URLs, audiences).
- Proceso documentado para crear nueva managed policy (SLA, requisitos, approval).
- Rotación de secretos OAuth coordinada con calendario operacional.
- Mantener y revisar el `agentcore-prd-emergency-destroyer` role + lista de principals autorizados.

**Métrica de servicio:**
- Tiempo desde request de nueva managed policy hasta disponibilidad < 5 días.
- Audit trimestral de quién tiene acceso al emergency destroyer role.

### 3.4 Seguridad (Monitoreo + Cedar Policies)

**Compromiso:**
- Definir el threshold de severity para `scan_image` (recomendado HIGH).
- Operar el SNS topic de drift detection y alertas de pipeline.
- Revisar Cedar policies en `LOGONLY` antes de promover a `ENFORCE`.
- Auditar logs de `pipeline_telemetry` periódicamente.
- Investigar drifts categorizados como `critical` o `high`.
- Mantener catálogo de Cedar policy templates aprobados (igual que managed policies).

**Métrica de servicio:**
- Tiempo de respuesta a alerta `critical` < 1 hora en horario hábil.
- Cobertura de Cedar policies en gateways de PRD > 90% de los workloads expuestos.

### 3.5 FinOps (Costos)

**Compromiso:**
- Definir whitelist de modelos LLM permitidos por ambiente en `allowed_models.yml`.
- Aprobar promoción de modelos costosos (ej: Opus) a PRD con análisis de costo.
- Operar dashboard de costos por capability/owner basado en tags AWS.
- Definir umbrales de alerta (mensual, por capability).

**Métrica de servicio:**
- Costo mensual por agente productivo dentro de banda objetivo.
- Reportes mensuales de uso de tokens por modelo a stakeholders.

### 3.6 equipo central de IA / Equipos consumidores

**Compromiso (estos son los CONSUMIDORES de la plataforma, no operadores):**
- Adoptar la plataforma como camino estándar (no construir alternativas paralelas).
- Reportar fricciones y solicitudes de features al equipo de plataforma.
- Mantener el manifest de cada workload actualizado.
- Capacitar a sus devs en el uso del manifest opinado.
- Participar en retrospectivas trimestrales con el equipo de plataforma.

### 3.7 Equipo de Plataforma (NUEVO — clave)

**Este equipo NO existe aún en la mayoría de organizaciones y debe crearse explícitamente.** Es **distinto al equipo central de IA** — el equipo central de IA construye agentes, este equipo construye la plataforma sobre la cual los agentes se construyen.

**Composición mínima recomendada:**

| Rol | Cantidad | Perfil |
|---|---|---|
| **Tech Lead** | 1 | Senior, orquesta el equipo, decide arquitectura, hace tradeoffs técnicos. Idealmente con experiencia en Platform Engineering en organizaciones reguladas. |
| **DevOps senior** | 1-2 | Fuerte en GitLab CI, Terraform, AWS. Responsable de la robustez del pipeline. |
| **Ingenieros de IA / AgentCore** | 1-2 | Conocimiento profundo de Bedrock AgentCore, sus quirks, sus límites. Acompañan a equipos consumidores en casos complejos. |
| **Product Manager / Owner transversal** | 1 | Conoce los procesos de la organización de punta a punta. Destraba burocracias entre áreas. Prioriza el backlog del equipo. Crítico para que la plataforma no se atasque políticamente. |
| **(opcional) SRE** | 0-1 | Cuando la plataforma supere 50+ agentes en PRD. Operación de telemetría, drift, alertas. |

**Tamaño total**: 4-7 personas. Este equipo es full-time dedicado a la plataforma. Sin ese commitment, la plataforma se atrofia en 6-12 meses.

**Responsabilidades:**
- Mantener y evolucionar los 8 repos del framework (`Componentes`, `Compose`, `Infra`, `AgentPlatform`, deployables).
- Operar el ciclo de release semver de cada repo.
- Onboarding y soporte de equipos consumidores.
- Roadmap de la plataforma según `01_IMPROVEMENTS_AND_FUTURE_WORK.md`.
- Coordinar con DevOps, CloudOps, Accesos, Seguridad, FinOps.
- Comunicación: changelogs, retros, demos.

---

## 4. Camino hacia IA descentralizada

Este framework es una **base correcta para transicionar a un esquema de IA descentralizado** donde no todo corra en las 3 cuentas centrales del equipo central. Eso ocurrirá inevitablemente cuando:

- Distintas business units tengan compliance / data residency / regulatorio diferenciados.
- Las quotas centrales se vuelvan limitantes a pesar del sharding.
- Algunas BUs quieran su propio ciclo de innovación sin pasar por el equipo central de IA.

### Cómo el framework habilita la descentralización

1. **Multi-account ya soportado:** el patrón de shards es directamente extensible a "cuenta por business unit". `metadata.target_shard` puede pasar de `prd-shard-a` a `bu-finance-prd`.
2. **Composiciones reusables:** una BU que monta su propia cuenta puede consumir las mismas composiciones de `Infra-AgentCore` con su propio deployable. Sin re-implementar nada.
3. **Whitelists locales:** cada BU puede mantener su propio fork curado de `allowed_models.yml` con políticas internas, mientras hereda las globales.
4. **Federación de gateways:** cuando aparezca el caso, agentes en cuenta-A pueden invocar tools registradas en gateway de cuenta-B usando OAuth o SigV4 cross-account (ya soportado por AgentCore Identity).
5. **Catálogo descubrible cross-tenant:** LeanIX (o equivalente) ya recibe metadata de todos los manifests; permite que la BU-X descubra agentes de la BU-Y.

### Lo que requeriría la transición a descentralizado

- **Plataforma central como SaaS interno:** el equipo de plataforma deja de operar workloads y opera la plataforma para que cada BU opere sus propios. Cambia el contrato.
- **Federación de identidad:** OAuth issuer central + per-BU issuers federados.
- **Cross-tenant policies Cedar:** el policy engine necesita poder evaluar `principal.tenant == "bu-finance"`.
- **Cost showback / chargeback** entre tenants.

Esto es Fase 10+ en el roadmap. **No es trabajo a iniciar ahora.** Pero el framework actual no tiene decisiones que lo bloqueen — es expandible en esta dirección.

---

## 5. Trabajo futuro: el "golden standard"

A largo plazo (12-24 meses), la plataforma debería evolucionar hacia un **chasis de desarrollo de agentes IA** — un framework empresarial con DX excepcional pero gobierno radical bajo el capó.

### `agentcore-company-cli` — el aceleramiento ×100

Hoy un dev:
1. Clona `_template/`.
2. Edita manifest manualmente.
3. Push.
4. Espera 12 minutos.
5. Verifica logs en GitLab UI.

Con un CLI bien diseñado:
1. `agentcore-cli new chatbot --capability customer-support` (genera todo desde un wizard).
2. `agentcore-cli validate` (chequea manifest local en 2 segundos).
3. `agentcore-cli preview-tfvars` (muestra qué Terraform se va a aplicar).
4. `agentcore-cli deploy --env dev` (push + tail de logs en consola con TRACE_ID).
5. `agentcore-cli logs --trace-id abc123` (sin entrar a CloudWatch).
6. `agentcore-cli rollback` (mueve alias `live` a versión anterior).

**Lo importante:** el CLI sigue **respetando todos los guardrails** del framework (whitelists, validaciones, gates). Solo elimina la fricción de UX.

### Otros componentes del golden standard

- **Backstage / portal interno** con catálogo de agentes, MCPs, tools, modelos disponibles, ownership.
- **Marketplace interno**: equipo A descubre tool de equipo B y la reusa con `git+ref` sin copiar código.
- **A/B testing harness** para comparar modelos en producción con tráfico shadow.
- **Cost showback automático** por capability/owner directamente en el portal.
- **Compliance reports auto-generados**: "Estos son todos los agentes en PRD, sus modelos, sus prompts, sus permisos, sus policies Cedar, sus owners."

---

## 6. Debilidades y consideraciones a tener en cuenta

> Estas son honestas. Toda plataforma tiene tradeoffs. Si una junta directiva no las conoce, se sorprenderá negativamente cuando aparezcan.

### Debilidades estructurales

1. **Curva de aprendizaje alta para devs nuevos.**
   - Onboarding de un dev junior puede tomar 2-3 semanas hasta que entienda el manifest, los componentes, el flujo end-to-end, AgentCore, Cedar.
   - **Mitigación:** documentación viva, starter kit, eventualmente CLI.

2. **Dependencia fuerte del equipo de plataforma.**
   - Si el equipo se desmantela o pierde personas clave, la plataforma se atrofia rápido.
   - **Mitigación:** documentación exhaustiva, redundancia de roles, rotación entre equipo de plataforma y equipo central de IA.

3. **Provider AWS Terraform inmaduro para AgentCore.**
   - AgentCore es un servicio nuevo (2025-2026). Recursos como `policy_engine` aún no existen en el provider; usamos workarounds `local-exec`.
   - **Mitigación:** vigilancia trimestral de releases del provider, migración cuando los recursos nativos aparezcan.

4. **Estado fragmentado de Terraform.**
   - State en GitLab managed state, distribuido entre N proyectos deployable. Si GitLab cae, no hay deploys.
   - **Mitigación:** backup off-site del state, runbook de recovery, considerar S3 backend secundario.

5. **Costo operacional del equipo de plataforma.**
   - 4-7 personas full-time es una inversión real (~USD 600K-1.5M/año en una organización chilena, mucho más en EU/US).
   - **Justificación:** sin este equipo, la organización paga el costo en cada equipo de IA (cada uno reinventando la rueda) — costo total mayor pero diluido.

### Riesgos de adopción

1. **"Demasiada complejidad para mi caso simple"** — equipos con un solo agente trivial pueden percibir la plataforma como overkill.
   - **Realidad:** Fase 1 está diseñada exactamente para ese caso. Si una BU genuinamente solo va a tener 1-2 agentes, podría tener sentido un atajo. Si va a tener 10+, la plataforma se justifica.

2. **"Mi equipo no puede esperar a la Fase X"** — algún equipo querrá Cedar policies o sharding antes de la Fase prevista.
   - **Mitigación:** roadmap claro, comunicación frecuente, capacidad de adelantar fases si hay business case fuerte.

3. **"Voy a buildar mi propia plataforma porque la del equipo central no me sirve"** — fragmentación organizacional.
   - **Mitigación:** trabajo proactivo de evangelización, métricas visibles de adopción, comunicación ejecutiva del compromiso con la plataforma única.

### Limitaciones técnicas conocidas

1. AgentCore Runtime no soporta zip directo desde S3 — exige imagen ECR ARM64. Workaround: zip auditable en S3 + build de imagen en pipeline.
2. ENIs pueden quedar huérfanas en destroy del runtime (issue #45099 del provider).
3. Cedar resource ARNs no admiten wildcards — fuerza deploy en 2 fases para gateways nuevos.
4. Provider AWS no expone `aws_bedrockagentcore_policy_engine` aún — workaround con CLI `agentcore` y `local-exec`.

---

## 7. Resumen ejecutivo en 1 página

**Qué construimos:** una plataforma interna que permite a cientos de equipos desplegar agentes IA, MCP servers y tools en AWS Bedrock AgentCore con self-service, gobierno fuerte y multi-cuenta desde el día uno.

**Por qué importa:** sin esta plataforma, cada equipo reinventa CI/CD, IAM, monitoreo, gobierno. La organización fragmenta prácticas, gasta más, audita peor, y va más lento.

**Qué pedimos a cada área:**
- DevOps: runners + GitLab.
- CloudOps: cuentas AWS + foundation + quota management.
- Accesos: managed policies + IdP + emergency role.
- Seguridad: thresholds + drift response + Cedar review.
- FinOps: whitelist modelos + dashboards de costo.
- equipo central de IA: adopción de la plataforma como camino estándar.

**Qué requiere crearse explícitamente:** un **equipo de plataforma de 4-7 personas** distinto al equipo central, con DevOps senior + ingenieros de IA + Product Manager transversal + Tech Lead. Sin este equipo, la inversión se pierde.

**Cuándo veremos valor:** Fase 1 (8 semanas) entrega el primer agente desplegado en DEV. Fase 4 (semana 16) tenemos PRD operativo. Fase 7 (semana 24) escalamos horizontalmente con sharding.

**Cuál es el riesgo:** la plataforma sin equipo dedicado se atrofia. La adopción sin acompañamiento ejecutivo se fragmenta. Las dos cosas son problemas organizacionales, no técnicos. La tecnología está lista; la organización tiene que decidir comprometerse.

**Cuál es el techo:** transitamos eventualmente a un esquema descentralizado por business unit, con federación de identidad y gateways. La plataforma actual es la base correcta para eso. No es un cul-de-sac arquitectónico.
