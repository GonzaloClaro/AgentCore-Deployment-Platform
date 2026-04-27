# Runbook: Destroy en PRD

> **Último recurso.** Casi nunca debería ejecutarse. Si dudas, NO lo hagas.

## Defensa en profundidad implementada

| Capa | Mecanismo | Ubicación |
|---|---|---|
| 1 | IAM Deny en role `deployer` PRD para `bedrock-agentcore:Delete*` y KMS scheduled deletion | `foundation/bootstrap/main.tf` (output `deployer_deny_policy_arn`) |
| 2 | Role separado `agentcore-prd-emergency-destroyer` con MFA + lista cerrada de principals | `foundation/bootstrap/main.tf` (output `emergency_destroyer_role_arn`) |
| 3 | Manual gate adicional `prd-destroy-acknowledge` en `pipeline_infra.yml` cuando plan incluye destroys | `Compose-AgentCore/pipeline_infra.yml` |

Cualquiera por sí solo no garantiza protección. Los 3 juntos sí.

## Caso 1: Workload completo a destruir (descontinuación de un agente)

**Pre-requisitos:**
- Aprobación de CAB documentada (ticket).
- Verificación con owner del workload de que no hay tráfico vivo (CloudWatch metrics `Invocations` = 0 los últimos 7 días).
- Backup del state actual del workload (export):
  ```bash
  terraform state pull > /secure-backup/<workload>-prd-state-$(date +%Y%m%d).json
  ```

**Pasos:**

1. En el repo del workload (`AgentPlatform`), eliminar el directorio `agents/<capability>/<name>/` y hacer MR a `main`.
2. El pipeline detectará que ya no existe → no genera plan para ese workload (no aplica destroy automáticamente porque el state queda huérfano, no removido).
3. **Destroy explícito:** correr el pipeline `pipeline_infra.yml` del deployable PRD apuntando al workload específico:
   - Trigger manual con variable `TF_ACTION=destroy` y `WORKLOAD=<name>`.
   - El job `terraform-plan` mostrará destroys → automáticamente aparece `prd-destroy-acknowledge` job.
   - Approver clicked en `prd-destroy-acknowledge` (Capa 3).
   - Approver clicked en `terraform-apply` (manual gate normal de PRD).
4. Si Capa 1 (IAM Deny) está attachada al role del deployer, el apply fallará con `AccessDenied`.
5. Operador autorizado asume `agentcore-prd-emergency-destroyer` con MFA reciente:
   ```bash
   aws sts assume-role \
     --role-arn arn:aws:iam::<PRD-ACCOUNT>:role/agentcore-prd-emergency-destroyer \
     --role-session-name destroy-<ticket>-$(date +%s) \
     --serial-number <YOUR-MFA-DEVICE-ARN> \
     --token-code <CURRENT-MFA-CODE>
   ```
6. Re-corre el `terraform-apply` (con vars del role asumido). Esta vez el destroy procede.
7. Verificar en consola AWS que recursos se hayan destruido (runtime, alias, memory, KB si aplicaba).
8. **Re-attachar el deny policy** al role deployer (si se quitó temporalmente).
9. Cerrar el ticket de CAB con captura de evidencia.

## Caso 2: ENI orphans tras destroy de runtime (issue #45099 del provider)

Síntoma: el destroy del runtime "completó" pero hay ENIs huérfanas en la VPC consumiendo IPs.

```bash
# Listar ENIs orphan
aws ec2 describe-network-interfaces \
  --filters "Name=description,Values=*bedrock-agentcore*" \
            "Name=status,Values=available" \
  --query 'NetworkInterfaces[].[NetworkInterfaceId,Description,VpcId]' \
  --output table

# Borrar las que están sin attachment
aws ec2 delete-network-interface --network-interface-id <ENI-ID>
```

Documentar en el ticket de CAB qué ENIs se borraron.

## Caso 3: KMS key marcada para deletion accidentalmente

Capa 1 (deny policy) bloquea `kms:ScheduleKeyDeletion` para los KMS keys de artifacts y secrets. Si por alguna razón el deny no aplicó:

```bash
# CANCELAR el scheduled deletion (window default = 30 días)
aws kms cancel-key-deletion --key-id <KEY-ID>
```

Tienes 30 días para reaccionar. Pasa esa ventana, los datos cifrados con esa key son **irrecuperables**.

## Caso 4: State file corrupto / desincronizado

Si `terraform plan` muestra resource changes que no corresponden con la realidad:

1. **NO hacer apply.** El plan está usando un state desactualizado.
2. Backup del state:
   ```bash
   terraform state pull > /secure-backup/state-broken-$(date +%Y%m%d-%H%M).json
   ```
3. Refrescar state:
   ```bash
   terraform refresh
   ```
4. Re-correr plan. Si sigue con discrepancias, hay drift real → procedimiento normal de drift remediation.
5. Si el state mismo está corrupto (no parsea), restaurar desde versión previa de GitLab managed state UI:
   - GitLab → proyecto → Operate → Terraform States → ver historial → revertir.

## Anti-patrones — qué NO hacer en PRD

- ❌ `terraform destroy` sin pasar por el pipeline (saltea Capa 3 y audit trail).
- ❌ Quitar permanentemente el deny policy "porque molesta" (saltea Capa 1, expones la cuenta).
- ❌ Asumir el `emergency-destroyer` para cambios "rápidos" no relacionados a destroy. Ese role tiene `AdministratorAccess` — su uso debe ser excepcional y auditado.
- ❌ `terraform state rm` para "saltar" el destroy. El recurso queda en AWS sin TF tracking → ahora tienes recurso unmanaged + drift permanente.
- ❌ Hacer destroy "por las dudas" sin verificar con el owner del workload. Cientos de agentes = tráfico real impredecible.

## Métricas a vigilar post-destroy

- CloudWatch metric `Invocations` del runtime debería caer a 0.
- CloudTrail debería mostrar `DeleteAgentRuntime` con el `assumeRoleArn` correcto (= emergency destroyer).
- ENIs en la VPC (chequear count antes/después).
- Costos: la cuenta PRD debería bajar costos del runtime destruido (visible en Cost Explorer al día siguiente).
