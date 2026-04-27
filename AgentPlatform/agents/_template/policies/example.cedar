// Ejemplo de Cedar policy para AgentCore Gateway.
//
// Semántica:
//   - Default DENY (sin permit explícito → deny).
//   - FORBID wins sobre permit.
//   - Layering: todas las policies aplicables deben permitirlo.
//
// Principals: AgentCore::OAuthUser (3LO/2LO) | AgentCore::IamEntity (SigV4).
//
// Action format: AgentCore::Action::"<TargetName>___<tool_name>"
//   ⚠️ TRIPLE underscore entre TargetName y tool_name (no doble).
//
// Resource: AgentCore::Gateway::"<gateway-arn-completo>"
//   ⚠️ Cedar NO admite wildcards en resource. Hay que poner el ARN exacto del gateway.
//   ⚠️ Esto implica deploy en 2 fases: primero el gateway, luego retrieve ARN
//   con `agentcore status`, y finalmente actualizar el .cedar con el ARN real.
//   Para los 3 default gateways del ambiente, el ARN se conoce post-foundation.

// Permite a usuarios OAuth llamar las tools de lectura de pólizas
permit(
    principal is AgentCore::OAuthUser,
    action in [
        AgentCore::Action::"InsuranceAPI___get_policy",
        AgentCore::Action::"InsuranceAPI___get_claim_status"
    ],
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/oauth-3lo"
);

// Solo senior-adjusters o managers pueden actualizar coverage
forbid(
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"InsuranceAPI___update_coverage",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/oauth-3lo"
) unless {
    principal.hasTag("role") &&
    (principal.getTag("role") == "senior-adjuster" ||
     principal.getTag("role") == "manager")
};

// Restringir invocaciones M2M (SigV4) por cuenta AWS de origen
permit(
    principal is AgentCore::IamEntity,
    action == AgentCore::Action::"InternalAPI___sync_data",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/sigv4-m2m"
) when {
    principal.id like "*:111122223333:*"
};

// Condición sobre context.input — Cedar puede inspeccionar el payload del request
permit(
    principal is AgentCore::OAuthUser,
    action == AgentCore::Action::"InsuranceAPI___file_claim",
    resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-east-1:111122223333:gateway/oauth-3lo"
) when {
    context.input has claimType &&
    (context.input.claimType == "health" ||
     context.input.claimType == "property" ||
     context.input.claimType == "auto")
};
