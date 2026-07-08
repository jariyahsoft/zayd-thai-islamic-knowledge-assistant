CREATE INDEX IF NOT EXISTS idx_document_chunks_reference_lookup
  ON document_chunks (reference)
  WHERE is_published = true AND reference IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_normalized_trgm
  ON document_chunks
  USING GIN (content_normalized gin_trgm_ops)
  WHERE is_published = true;

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_normalized_tsv
  ON document_chunks
  USING GIN (to_tsvector('simple', content_normalized))
  WHERE is_published = true;

CREATE INDEX IF NOT EXISTS idx_documents_published_filters
  ON documents (review_status, language, madhhab, source_id, source_license_id)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_document_versions_published_filters
  ON document_versions (status, frozen_at, document_id);

CREATE INDEX IF NOT EXISTS idx_source_licenses_retrieval_filters
  ON source_licenses (status, embedding_permission, source_id);
