# Multi-account Sharding

> **Para qué sirve este doc:** estrategia de escalado horizontal cuando los workloads de un ambiente exceden las **quotas de servicio** de AgentCore en una sola cuenta AWS.

## El problema

AgentCore tiene quotas **por cuenta** que con cientos de agentes se vuelven el limitante:

| Recurso | Quota típica por cuenta |
|---|---|
| Agent Runtimes | ~100-500 (depende de region) |
| Memories | similar |
| Gateways | bajo (~50) |
| Knowledge Bases | similar |
| Lambda concurrency | 1000 simultáneas (default) |
| Bedrock TPM/RPM | por modelo y región |

Con cientos de agentes en PRD, **una sola cuenta `prd-agenticplatform` no escala**. Solución: **sharding por cuenta**.

## Modelo: deployable por shard

En lugar de 3 cuentas (dev/qa/prd), tenemos N por ambiente. Cada cuenta tiene su propio deployable bajo `iac/AgentCore/`:

```
iac/AgentCore/
├── infra-agentcore               # Código TF compartido (módulos + composiciones)
├── agentcore-dev                 # → cuenta dev-agenticplatform
├── agentcore-qa                  # → cuenta qa-agenticplatform
├── agentcore-prd-shard-a         # → cuenta prd-agenticplatform-a (cap 1-3)
├── agentcore-prd-shard-b         # → cuenta prd-agenticplatform-b (cap 4-7)
└── agentcore-prd-shard-c         # → cuenta prd-agenticplatform-c (cap 8-10)
```

Cada shard:
- Es un proyecto GitLab independiente
- Tiene su propio `env-defaults.yaml` con su `account_id`, VPC, KMS
- Tiene su propio Terraform state (GitLab managed)
- Tiene sus propios 3 default gateways (output de su `foundation/`)

## Cómo el workload elige shard

### Opción A (recomendada): explícito en metadata

```yaml
metadata:
  name: chatbot-tier1
  capability: customer-support
  target_shard: prd-shard-a   # ← decide a qué cuenta va en PRD
```

`render_tfvars` lee `target_shard` y `trigger_iac` apunta al deployable correspondiente.

### Opción B: tabla de routing por capability

`Compose-AgentCore/variables/shard-routing.yml`:

```yaml
capabilities:
  customer-support:  prd-shard-a
  finance:           prd-shard-b
  hr:                prd-shard-a
  fraud:             prd-shard-c     # capability sensible aislada en su shard
```

El manifest no declara shard; lo infiere el pipeline. Más declarativo, pero **un cambio de routing requiere migración** (state del workload está en el shard viejo).

**Default propuesto: Opción A.** Decisión explícita en el manifest = inmovilidad del routing = no hay sorpresas en disaster recovery.

## Cómo agregar una cuenta nueva

Cuando se llene la cuota de un shard:

1. **Provisionar nueva cuenta AWS** `prd-agenticplatform-d` (Control Tower / Account Factory).

2. **Crear nuevo proyecto GitLab** en `iac/AgentCore/agentcore-prd-shard-d` (clonar uno existente como template).

3. **Configurar CI variables** del nuevo proyecto:
   - `AWS_ROLE_ARN_PRD_SHARD_D` (masked, scope `prd`)
   - `AWS_ACCOUNT_ID_PRD_SHARD_D`

4. **Actualizar `env-defaults.yaml`** del nuevo deployable con valores reales (account_id, VPC, KMS).

5. **Aplicar `foundation/`** en la nueva cuenta:
   ```bash
   terraform -chdir=foundation/bootstrap apply -var environment=prd-shard-d
   terraform -chdir=foundation/default-gateways apply
   terraform -chdir=foundation/vpc-endpoints apply  # si aplica
   ```

6. **Tomar outputs** y pegar en `env-defaults.yaml`:
   - `kms_artifacts_arn`, `kms_secrets_arn`
   - `runtime_role_arn`
   - `default_gateway_ids.{oauth_3lo, oauth_2lo, sigv4_m2m}`
   - `s3_artifact_buckets.{agents, mcp, tools}`

7. **Agregar al schema** del manifest el nuevo valor de `target_shard`:
   ```json
   "target_shard": {
     "enum": ["dev", "qa", "prd-shard-a", "prd-shard-b", "prd-shard-c", "prd-shard-d"]
   }
   ```

8. **Actualizar `Compose-AgentCore/rules/branch-to-env.yml`** con el routing al nuevo TARGET_IAC_PROJECT.

9. **(Opcional)** Migrar agentes específicos del shard A al D:
   - Cambiar `target_shard` en sus manifests
   - **Importante:** esto hace destroy en A + create en D. Si el agente tiene state (memory, KB), planear migración.

## Costo de operación

| Métrica | Por shard | 1 cuenta sin shard |
|---|---|---|
| Cuentas AWS a operar | N (mayor costo de gobierno cuenta) | 1 (más simple) |
| Quotas de AgentCore | N veces | 1 vez |
| Bedrock TPM | N veces (cada cuenta tiene su quota) | 1 vez |
| Permission complexity | mayor (cross-account) | menor |
| Disaster recovery | mejor (blast radius limitado a 1 shard) | peor (caída de 1 cuenta = caída total) |
| Tracking de costos | más fácil per-shard | requiere tags |

## Cuándo justificar un shard nuevo

Métricas que disparan el sharding:

- > 60% de quota de **agent-runtime per account** consumida
- Bedrock **TPM** consistentemente > 70% del límite del modelo más usado
- **Lambda concurrency** > 500 simultánea sostenido (de los tools-lambda)
- Capability con **requisitos regulatorios distintos** (ej: fraud aislado por compliance)
- Capability con **tenant aislado** (ej: white-label que requiere su propia cuenta)

## Anti-patrones

- ❌ **Auto-balancing de shards.** Tentador pero peligroso: un workload que cambia de cuenta sin que el dev lo decida = caos en disaster recovery.
- ❌ **Sharding por agente.** No por agente individual, por capability o tenant. Granularidad demasiado fina = explosión combinatoria de cuentas.
- ❌ **Shards sin foundation aplicado.** Cada shard nuevo necesita los 3 default gateways y bootstrap. Sin esto, los workloads fallan al hacer plan/apply.
- ❌ **Cross-shard dependencies.** Un agente en `prd-shard-a` que depende de un MCP en `prd-shard-b` requiere config cross-account compleja. Mantener todo lo que necesita un agente **dentro de su shard**.
