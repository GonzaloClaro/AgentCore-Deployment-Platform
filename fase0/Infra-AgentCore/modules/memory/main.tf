resource "aws_bedrockagentcore_memory" "this" {
  name                  = var.name
  description           = var.description
  event_expiry_duration = var.event_expiry_seconds
  tags                  = merge(var.tags, { ManagedBy = "agentcore-pipeline" })
}

resource "aws_bedrockagentcore_memory_strategy" "strategies" {
  for_each = { for s in var.strategies : s.name => s }

  memory_id  = aws_bedrockagentcore_memory.this.id
  name       = each.value.name
  type       = each.value.type # SUMMARIZATION | SEMANTIC | USER_PREFERENCE
  namespaces = each.value.namespaces

  dynamic "configuration" {
    for_each = each.value.configuration != null ? [each.value.configuration] : []
    content {
      type = configuration.value.type
    }
  }
}
