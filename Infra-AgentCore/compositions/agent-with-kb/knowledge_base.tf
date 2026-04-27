# Bedrock Knowledge Base con S3 Vectors.
# Solo se crea si var.knowledge_base.sources tiene al menos una fuente.

module "knowledge_base" {
  count  = local.has_kb ? 1 : 0
  source = "../../modules/knowledge-base"

  name                = "${local.runtime_name}-kb"
  description         = "KB para ${local.runtime_name}"
  role_arn            = var.default_role_arn
  embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/${lookup(var.knowledge_base, "embedding", "amazon.titan-embed-text-v2:0")}"
  embedding_dimension = 1024
  sources             = lookup(var.knowledge_base, "sources", [])
  tags                = local.base_tags
}
