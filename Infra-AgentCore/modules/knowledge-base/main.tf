# modules/knowledge-base
# Bedrock Knowledge Base con S3 Vectors como backend.
# Soporta semantic search (no hybrid; limitación de S3 Vectors).

resource "aws_s3vectors_vector_bucket" "kb" {
  vector_bucket_name = "kb-${var.name}"

  # encryption_configuration en provider 6.x es atributo (lista de objeto), no bloque.
  # El object type requiere AMBOS keys: sse_type y kms_key_arn (este último null para AES256).
  encryption_configuration = [{
    sse_type    = "AES256"
    kms_key_arn = null
  }]
}

resource "aws_s3vectors_index" "kb" {
  vector_bucket_name = aws_s3vectors_vector_bucket.kb.vector_bucket_name
  index_name         = var.name
  data_type          = "float32"
  dimension          = var.embedding_dimension
  distance_metric    = "cosine"
}

resource "aws_bedrockagent_knowledge_base" "this" {
  name        = var.name
  description = var.description
  role_arn    = var.role_arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn
    }
  }

  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration {
      vector_bucket_arn = aws_s3vectors_vector_bucket.kb.vector_bucket_arn
      index_arn         = aws_s3vectors_index.kb.index_arn
    }
  }

  tags = merge(var.tags, { ManagedBy = "agentcore-pipeline" })
}

resource "aws_bedrockagent_data_source" "sources" {
  for_each          = { for s in var.sources : s.name => s }
  knowledge_base_id = aws_bedrockagent_knowledge_base.this.id
  name              = each.value.name

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = each.value.bucket_arn
      inclusion_prefixes = each.value.inclusion_prefixes
    }
  }
}
