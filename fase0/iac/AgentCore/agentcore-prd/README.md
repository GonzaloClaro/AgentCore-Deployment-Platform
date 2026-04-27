# agentcore-prd

> **Tipo:** Proyecto deployable Terraform (cuenta `prd-agenticplatform`)
> **State:** GitLab-managed Terraform state (per-project)

Mismo patrón que `agentcore-dev` y `agentcore-qa`. Particularidades:

- Apunta a cuenta PRD (`assume-role` distinto).
- `env-defaults.yaml` con IDs de la cuenta PRD.
- Pipeline tiene **manual approval gate** antes de `terraform apply`.
- Consume **siempre** `INFRA_REF` con tag inmutable `vX.Y.Z` (nunca `main`).
- El runtime se promueve via **alias `live` apuntado a una versión inmutable**, no apply in-place.

Ver `agentcore-dev/README.md` para detalles del flujo.

## Cambios destructivos

Para destroy (raro en PRD), seguir runbook documentado y considerar issue #45099 (ENIs huérfanas).
