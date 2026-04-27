# Quotas de AWS Bedrock AgentCore — análisis de capacity planning

> **Audiencia:** equipo de plataforma + CloudOps + FinOps. **Objetivo:** anticipar cuándo y dónde van a pegar las quotas, y qué hacer cuando ocurra.

> **Fuente oficial:** [AWS Bedrock AgentCore Service Quotas](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html). Datos validados a abril 2026. **Reverificar trimestralmente** porque AgentCore es un servicio joven y las quotas suben con frecuencia.

## Índice

1. [Quotas críticas para capacity planning](#1-quotas-críticas-para-capacity-planning)
2. [Quotas detalladas por servicio](#2-quotas-detalladas-por-servicio)
3. [Escenarios de saturación](#3-escenarios-de-saturación)
4. [Mitigaciones automáticas](#4-mitigaciones-automáticas)
5. [Mitigaciones via sharding](#5-mitigaciones-via-sharding)
6. [Quotas de Bedrock (modelos) — relacionadas pero distintas](#6-quotas-de-bedrock-modelos--relacionadas-pero-distintas)
7. [Capacity planning calculadora](#7-capacity-planning-calculadora)

---

## 1. Quotas críticas para capacity planning

Estas son las que pegan primero en organizaciones grandes. Vigilancia cercana.

| Quota | Default | Adjustable | Cuándo pega típicamente |
|---|---|---|---|
| **Active session workloads / cuenta** | 1,000 (us-east-1, us-west-2); 500 (otras regiones) | ✅ sí | Tráfico concurrente alto. Cada session activa cuenta. |
| **Total agents / cuenta** | 1,000 | ✅ sí | Cuando hay >1000 runtimes únicos en producción. |
| **Memory resources / cuenta** | 150 | ✅ sí | **PEGA RÁPIDO** — solo 150 memorias por cuenta. Forzará sharding antes de los runtimes. |
| **Gateways / cuenta** | 1,000 | ✅ sí | Con 3 default + N custom, raro saturar antes que otros. |
| **Targets / gateway** | 100 | ✅ sí | Pega cuando un gateway agrupa muchas tools. |
| **Resource OAuth2 credential providers / cuenta** | 50 | ❌ NO | **PEGA TEMPRANO** — 50 OAuth providers por cuenta es un techo bajo. |
| **Resource API key credential providers / cuenta** | 50 | ❌ NO | Similar al anterior. |
| **Workload identities / cuenta** | 1,000 | ❌ NO | Cada runtime crea uno automáticamente — pega junto con runtimes. |
| **Policy engines / cuenta** | 1,000 | ❌ NO | Cedar policy engines. |
| **Policies / engine** | 1,000 | ❌ NO | Suficiente para casos normales. |
| **InvokeAgentRuntime API rate / agent** | 25 TPS | ✅ sí | Tráfico real alto en un agente popular. Pedir aumento es trivial. |

> Los **non-adjustable** (❌) son los que más preocupan porque no se pueden subir con un ticket. Son los disparadores de sharding más probables.

---

## 2. Quotas detalladas por servicio

### 2.1 AgentCore Runtime

#### Recursos

| Quota | Default | Adjustable |
|---|---|---|
| Active session workloads / cuenta (us-east-1, us-west-2) | 1,000 | ✅ |
| Active session workloads / cuenta (otras regiones) | 500 | ✅ |
| Total agents / cuenta | 1,000 | ✅ |
| Versions / agent | 1,000 | ✅ |
| Endpoints (aliases) / agent | 10 | ✅ |
| Maximum Docker image size | 2 GB | ❌ |
| Maximum compressed code deployment package | 250 MB | ❌ |
| Maximum uncompressed code deployment package | 750 MB | ❌ |
| Maximum hardware allocation / session | 2 vCPU / 8 GB | ❌ |

#### Invocación

| Quota | Default | Adjustable |
|---|---|---|
| Request timeout | 15 min | ❌ |
| Maximum payload size | 100 MB | ❌ |
| Streaming chunk size | 10 MB | ❌ |
| Streaming maximum duration | 60 min | ❌ |
| Asynchronous job maximum duration | 8 h | ❌ |
| WebSocket frame size | 64 KB | ❌ |
| Idle session timeout | 15 min (configurable via `idleRuntimeSessionTimeout`) | ✅ |
| Maximum session duration | 8 h (configurable via `maxLifetime`) | ✅ |

#### Throttling (TPS = transacciones/segundo)

| Quota | Default | Adjustable |
|---|---|---|
| InvokeAgentRuntime / agent / cuenta | 25 TPS | ✅ |
| InvokeAgentRuntimeCommand / agent / cuenta | 25 TPS | ✅ |
| InvokeAgentRuntimeWithWebSocketStream / agent / cuenta | 25 TPS | ✅ |
| New sessions / endpoint (container deployment) | 100 TPM | ✅ |
| Direct code deploy new session rate / endpoint | 25 TPS | ✅ |
| WebSocket frame rate / connection | 250 frames/sec | ❌ |
| CreateAgentRuntime / Update / Delete | 5 TPS each | ✅ |
| GetAgentRuntime / GetEndpoint | 50 TPS | ✅ |
| List* | 5 TPS | ✅ |

#### Session storage

| Quota | Default | Adjustable |
|---|---|---|
| Maximum storage size | 1 GB | ❌ |
| Maximum filesystem metadata | ~50 MB (~100k-200k archivos) | ❌ |
| Maximum directory depth | 200 levels | ❌ |
| Maximum filename length | 255 bytes | ❌ |
| Maximum symlink target length | 4,095 bytes | ❌ |

### 2.2 AgentCore Memory

#### Recursos

| Quota | Default | Adjustable |
|---|---|---|
| **Memory resources / cuenta / region** | **150** | ✅ |
| Memory strategies / Memory resource | 6 | ❌ |
| Maximum memory strategies / cuenta | 900 | ✅ |
| Min EventExpirationDuration | 7 días | ❌ |
| Max EventExpirationDuration | 365 días | ❌ |
| Max prompt size (AppendToPrompt) | 30 KB | ❌ |
| Max messages / CreateEvent | 100 | ❌ |
| Max message size / CreateEvent | 100 KB | ❌ |
| Max event size / CreateEvent | 10 MB | ❌ |
| Max tokens/min long-term memory extraction | 150,000 | ✅ |
| Max tokens/min episodic per session | 50,000 | ❌ |

#### API throttling

| Quota | Default | Adjustable |
|---|---|---|
| CreateMemory / Delete / Update | 3 TPS | ✅ |
| GetMemory / List | 5 TPS | ✅ |
| CreateEvent | 10 TPS | ✅ |
| CreateEvent (with conversational payloads) / actor / session | 5 TPS | ❌ |
| CreateEvent (without conversational) / actor / session | 10 TPS | ❌ |
| DeleteEvent | 20 TPS | ✅ |
| DeleteEvent / actor / session | 5 TPS | ✅ |
| RetrieveMemoryRecords | 30 TPS | ✅ |
| ListMemoryRecords | 30 TPS | ✅ |

### 2.3 AgentCore Identity

| Quota | Default | Adjustable |
|---|---|---|
| **Workload identities / cuenta / region** | **1,000** | ❌ |
| **Resource OAuth2 credential providers / cuenta / region** | **50** | ❌ |
| **Resource API key credential providers / cuenta / region** | **50** | ❌ |

> Las 3 son **no adjustable**. Las 2 últimas (50 OAuth + 50 API key) son los techos más bajos del servicio. Forzarán sharding apenas haya >40 workloads con OAuth.

### 2.4 AgentCore Gateway

| Quota | Default | Adjustable |
|---|---|---|
| Gateways / cuenta | 1,000 | ✅ |
| Targets / gateway | 100 | ✅ |
| Tools / target | 1,000 | ✅ |
| Tool name char limit | 256 | ✅ |
| Maximum inline schema size | 1 MB | ✅ |
| Maximum S3 payload schema size | 10 MB | ✅ |
| Timeout gateway invocation | 15 min | ✅ |
| Concurrent target operations / gateway | 5 | ✅ |
| Tool-call concurrent / gateway | 1,000 | ✅ |
| Tool-call concurrent / cuenta | 1,000 | ✅ |
| Search-based tool-call rate | 25 TPM | ✅ |
| Maximum tool-call payload size | 6 MB | ✅ |

### 2.5 AgentCore Policy (Cedar)

| Quota | Default | Adjustable |
|---|---|---|
| Policy engines / cuenta / region | 1,000 | ❌ |
| Policies / engine | 1,000 | ❌ |
| Generated policies (7-day rolling) / engine | 50,000 | ❌ |
| Maximum policy size | 10 KB | ❌ |
| Maximum total policy size / resource | 200 KB | ❌ |
| Cedar schema size | 100 KB | ❌ |
| **CreatePolicyEngine** | 1 TPS | ❌ |
| GetPolicyEngine / List / Get / List policy | 5 TPS | ❌ |
| CreatePolicy / Update / Delete / List | 5 TPS | ❌ |

> CreatePolicyEngine a 1 TPS es lento — agregar 100 engines toma 100 segundos. Vigilar en deploy de muchos workloads simultáneos.

### 2.6 AgentCore Browser

| Quota | Default | Adjustable |
|---|---|---|
| Concurrent active sessions / cuenta | 1,000 | ✅ (support ticket) |
| Total Browser tool configurations / cuenta | 1,000 | ✅ |
| Hardware / session | 1 vCPU / 4 GB | ❌ |
| Maximum file size / extension | 10 MB | ✅ |
| Maximum extensions / session | 10 | ✅ |
| Maximum size / profile | 50 MB | ✅ |
| Maximum profiles / cuenta | 100 | ✅ |
| Disk size | 10 GB | ❌ |
| Max proxies / session | 5 | ❌ |
| Max domain patterns / proxy | 50 | ❌ |
| Max total domain patterns | 100 | ❌ |

### 2.7 AgentCore Code Interpreter

| Quota | Default | Adjustable |
|---|---|---|
| Concurrent active sessions / cuenta | 1,000 | ✅ |
| Total Code Interpreter configurations / cuenta | 1,000 | ✅ |
| Hardware / session | 2 vCPU / 8 GB | ❌ |
| Disk size | 10 GB | ❌ |
| Maximum payload size | 100 MB | ❌ |

### 2.8 AgentCore Evaluations

| Quota | Default | Adjustable |
|---|---|---|
| Input tokens/min built-in evaluators | 200,000 | ❌ |
| Evaluations/min built-in | 100 | ❌ |
| Spans / on-demand evaluation | 1,000 | ❌ |
| On-demand evaluation payload size | 15 MB | ❌ |
| Evaluators / on-demand evaluation | 1 | ❌ |
| Input tokens / evaluation | 200,000 | ❌ |
| Active online evaluation configurations / cuenta | 100 | ❌ |

### 2.9 AgentCore Resource-Based Policies

| Quota | Default | Adjustable |
|---|---|---|
| Maximum policy size | 20 KB | ❌ |
| Maximum statements / policy | 100 | ❌ |

### 2.10 AWS Agent Registry

| Quota | Default | Adjustable |
|---|---|---|
| Maximum registries / cuenta / region | 5 | ✅ |
| API throttling (varios) | 5-50 TPS | ✅ |

---

## 3. Escenarios de saturación

Análisis de qué pega primero en escenarios típicos.

### Escenario A: 50 agentes simples en una cuenta

- 50 runtimes ✅ (techo 1,000)
- 50 memorias (uno por agente) — ✅ (techo 150) pero **33% de uso** ya
- 0-50 OAuth credential providers (depende de auth) — ⚠️ si todos usan OAuth, **100% del techo**
- 50 workload identities (auto-creadas) ✅

**Cuál pega primero:** OAuth credential providers (si todos los agentes usan OAuth a APIs externas).

### Escenario B: 200 agentes mixtos en una cuenta

- 200 runtimes ✅ (20% techo)
- **200 memorias — REBASA techo 150**, hay que pedir aumento o sharding
- 100-200 OAuth providers — **EXCEDE techo 50 hard limit**, requiere sharding
- 200 workload identities ✅

**Cuál pega primero:** OAuth providers (a las ~50 unidades) → memorias (a las ~150).

### Escenario C: 500 agentes simples sin OAuth (solo Bedrock invoke)

- 500 runtimes ✅ (50% techo)
- **500 memorias — EXCEDE techo 150 incluso con increase razonable**, requiere sharding
- 0 OAuth providers ✅
- 500 workload identities ✅

**Cuál pega primero:** memorias.

### Escenario D: 1,000 invocaciones/segundo a un solo agente popular

- InvokeAgentRuntime / agent: 25 TPS default — **rebasado 40×**
- Pedir increase a AWS Support — usualmente conceden hasta varios cientos de TPS.
- Si superas eso: agrupar agentes (ej: API gateway interno con load balancing) o sharding por capability.

**Cuál pega primero:** InvokeAgentRuntime TPS.

### Escenario E: 1 MCP gateway con 200 tools

- 1 gateway ✅
- **200 targets / gateway — EXCEDE techo 100** (adjustable)
- Pedir increase, alternativamente split en 2 gateways.

**Cuál pega primero:** targets per gateway.

### Escenario F: equipo testing intensivo creando policy engines

- CreatePolicyEngine 1 TPS — bottleneck en deploys masivos.

**Cuál pega primero:** rate de creación de policy engines.

---

## 4. Mitigaciones automáticas

### Quota increase via Service Quotas console

Para quotas adjustables (✅), pedir increase es trivial:
1. AWS Console → Service Quotas → AgentCore.
2. Buscar quota → Request quota increase.
3. AWS Support típicamente responde en 1-3 días para increases razonables (≤10× del default).

**Tracking automatizable:** un job programado puede consumir CloudWatch metrics y abrir tickets cuando se supere el 70%.

### Cross-region inference profiles (Bedrock model invocation)

Para mitigar throughput throttling de un modelo específico:
- Usar inference profile cross-region (ej: `us.anthropic.claude-3-5-sonnet-...`) en lugar de model_id directo.
- AWS rutea entre us-east-1, us-west-2, etc., sumando throughput.
- Soportado nativamente en el módulo `runtime` via campo `inference_profile_arn`.

### Idle session timeout reducido

Por default 15 min. Si los agentes terminan rápido:
- Bajar a 5 minutos para liberar sessions activas más rápido.
- Más sessions concurrentes posibles dentro del mismo techo de "active session workloads".

Configurable por workload via `manifest.spec.runtime.lifecycle` (extensión futura).

---

## 5. Mitigaciones via sharding

Cuando los increase no alcanzan o el quota es no-adjustable (❌), la solución es **multi-account sharding** (ver `MULTI_ACCOUNT.md`).

### Disparadores recomendados para shard nuevo

| Métrica | Threshold para nuevo shard |
|---|---|
| Active session workloads | > 60% del techo (ajustado) |
| Memorias creadas | > 100 (de 150 default) |
| OAuth credential providers | > 35 (de 50 hard limit) |
| Total agentes | > 600 (de 1,000) |
| InvokeAgentRuntime TPS sostenido | > 70% del increase otorgado |

### Sharding por dimensión de capability

Recomendación: dividir cuentas por **capability** o **business unit**, no por equipo o agente individual. Ejemplo:

```
prd-shard-customer:    capabilities customer-support, customer-onboarding, etc.
prd-shard-finance:     capabilities finance, treasury, fraud
prd-shard-ops:         capabilities operations, internal-tools
prd-shard-experiments: capabilities sandbox, research
```

Esto evita migraciones cuando un agente cambia de equipo (raro) y agrupa naturalmente la carga.

### Cómo detectar que se necesita un shard

1. **Manualmente:** revisar Service Quotas dashboard semanalmente. Tedioso.
2. **CloudWatch metrics + alertas:** AWS expone métricas de uso vs quota. Configurar alertas a 60%/80%/95%.
3. **Custom dashboard del equipo de plataforma:** consolidar uso de las 4-5 quotas críticas en un solo panel.

---

## 6. Quotas de Bedrock (modelos) — relacionadas pero distintas

Las quotas de invocación de modelos en Bedrock son **separadas** de las quotas de AgentCore. Pega frecuente en agentes activos.

### Modelos de Anthropic en Bedrock (us-east-1, abril 2026)

| Modelo | TPM (tokens/min) input | TPM output | RPM (requests/min) |
|---|---|---|---|
| Claude 3.5 Sonnet v2 | varies — pedir increase | varies | 4,000 default |
| Claude 3.5 Haiku | varies | varies | 4,000 default |
| Claude 3 Opus | menor (modelo costoso) | — | menor |

> Los valores exactos cambian frecuentemente. Consultar [Bedrock service quotas](https://docs.aws.amazon.com/general/latest/gr/bedrock.html) para data actualizada.

### Estrategias

1. **Cross-region inference profiles** — repartir entre regions, sumando throughput.
2. **Model fallback** — si PRIMARY (Sonnet) throttled, retry con FALLBACK (Haiku). Ya soportado en el helper de `agent.py` con extensión futura.
3. **Rate limiting en el agente** — cap de RPS antes de hit a Bedrock (se devuelve 429 al cliente).
4. **Provisioned throughput** (pagar throughput dedicado) — para casos críticos de SLA.

---

## 7. Capacity planning calculadora

### Hoja de ruta de quotas vs número de agentes (orientativa)

| Agentes en PRD | Cuentas (shards) recomendados | Disparador típico |
|---|---|---|
| 1-30 | 1 | OK con quotas default |
| 30-80 | 1 (con quota increases) | Memorias > 80, OAuth > 35 |
| 80-150 | 2 shards | OAuth providers (hard 50) + memorias |
| 150-400 | 3-5 shards | Sharding por capability |
| 400-1,000 | 5-10 shards | Patrón multi-tenant inicial |
| 1,000+ | 10+ shards | Federación / descentralización |

### Pregunta crítica para FinOps

Cada shard nuevo tiene costos fijos:
- **Costo de cuenta AWS** (cuotas mínimas, NAT gateway, VPC endpoints): ~USD 200-500/mes.
- **Costo operacional** (tiempo del equipo de plataforma para mantener N cuentas): variable según automation.
- **Costo de duplicación de KMS keys, S3 buckets, foundation**: marginal.

**Total marginal por shard nuevo:** ~USD 500-1,000/mes en costos puramente AWS, + tiempo humano. Cuando se pasa de 5+ shards la operación se justifica con dashboards y automation.

### Reverificación trimestral

AgentCore es un servicio joven. Las quotas suben con frecuencia. **Cada Q el equipo de plataforma:**

1. Verifica esta página contra la docs oficial.
2. Actualiza valores que cambiaron.
3. Re-evalúa los thresholds de sharding según uso real.
4. Reporta a FinOps si las proyecciones de costo cambiaron.

---

## Sources

- [Quotas for Amazon Bedrock AgentCore — AWS docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html)
- [Amazon Bedrock AgentCore endpoints and quotas — AWS General Reference](https://docs.aws.amazon.com/general/latest/gr/bedrock_agentcore.html)
- [Amazon Bedrock service quotas — AWS General Reference](https://docs.aws.amazon.com/general/latest/gr/bedrock.html)
- [AgentCore generated runtime observability — AWS docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-runtime-metrics.html)
