output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.this.id
}

output "knowledge_base_arn" {
  value = aws_bedrockagent_knowledge_base.this.arn
}

output "vector_bucket_arn" {
  value = aws_s3vectors_vector_bucket.kb.vector_bucket_arn
}

output "data_source_ids" {
  value = { for k, v in aws_bedrockagent_data_source.sources : k => v.id }
}
