CREATE INDEX IF NOT EXISTS idx_embedding_records_space_active
  ON embedding_records (model_configuration_id, provider_id, dimension, status)
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_embedding_records_hnsw_model_active
  ON embedding_records
  USING hnsw (embedding vector_cosine_ops)
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_documents_published_version_filters
  ON documents (published_version_id, review_status, language, madhhab)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_sources_vector_filters
  ON sources (source_type, language, reliability_level, is_active)
  WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_embedding_records_hnsw_model_active IS
  'HNSW cosine index for active pgvector embeddings; query path must also filter model_configuration_id, provider_id and dimension to isolate embedding spaces.';

COMMENT ON INDEX idx_embedding_records_space_active IS
  'Supports fail-closed vector retrieval by active embedding space and dimension before pgvector ordering.';
