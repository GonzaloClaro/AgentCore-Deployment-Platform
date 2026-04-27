# agentcore-qa

> **Tipo:** Proyecto deployable Terraform (cuenta `qa-agenticplatform`)
> **State:** GitLab-managed Terraform state (per-project)

Mismo patrón que `agentcore-dev`. Diferencias:

- Apunta a cuenta QA (`assume-role` distinto).
- `env-defaults.yaml` con IDs de la cuenta QA.
- Pipeline tiene **manual approval gate** antes de `terraform apply`.
- Consume típicamente un `INFRA_REF` con tag fijo (`vX.Y.Z`), no `main`.

Ver `agentcore-dev/README.md` para detalles del flujo.
