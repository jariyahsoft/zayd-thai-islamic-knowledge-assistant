# pgvector Search

Status: implemented for TASK-07-04.

Vector retrieval uses PostgreSQL `pgvector` for production ordering and the retrieval
service enforces all visibility gates before a result can be returned.

## Query Contract

`VectorSearchService` accepts a query embedding plus a `model_configuration_id`.
The query may also include `provider_id`, language, madhhab, source type, license
status, source language, reliability threshold, result window, and timeout.

The embedding space is isolated by all of these checks:

- `model_configurations.id` must match the requested model.
- `model_configurations.model_type = 'embedding'`.
- provider and model statuses must be `enabled` and not soft-deleted.
- if `provider_id` is supplied, it must match the model configuration provider.
- `embedding_records.model_configuration_id` must match the requested model.
- `embedding_records.provider_id` must match the resolved provider.
- `embedding_records.dimension` must match the query vector and configured dimension.

This prevents mixing embeddings created by incompatible providers, model names,
model revisions, or dimensions. Model revision is recorded in
`model_configurations.configuration_json.revision` and returned in result metadata
for audit and later retrieval-run traces.

## Visibility Gates

The retrieval query applies status and license filters in SQL, before ranking:

- `embedding_records.status = 'active'`
- `document_chunks.is_published = true`
- `documents.review_status = 'published'`
- `documents.published_version_id = document_versions.id`
- `document_versions.status = 'published'`
- `document_versions.frozen_at IS NOT NULL`
- `sources.is_active = true`
- `source_licenses.status IN ('persistent_private', 'persistent_redistributable')`
- `source_licenses.embedding_permission = 'allowed'`

License and publication checks are not post-filters. A hidden, suspended, draft,
or license-ineligible chunk is not part of the candidate set.

## Index Choice

The base schema already creates `idx_embedding_records_vector` as an HNSW index
on `embedding vector_cosine_ops` for active embeddings. Migration
`0011_pgvector_search` adds:

- `idx_embedding_records_space_active` for active model/provider/dimension lookup.
- `idx_embedding_records_hnsw_model_active` as an explicit active HNSW cosine
  index for pgvector ordering.
- filter-support indexes for published documents and active sources.

HNSW is the default because retrieval is read-heavy and expects low-latency
nearest-neighbor search without a training phase. Cosine distance matches the
normalized-vector contract from the embedding provider interface.

## Timeout Behavior

On PostgreSQL, vector search sets `SET LOCAL statement_timeout = :timeout_ms`
inside the unit-of-work transaction before executing the candidate query. The
service validates `timeout_ms` to the range `1..5000`. SQLite tests do not have
PostgreSQL statement timeouts; they validate the same input contract and return
the configured timeout in result metadata.

## Maintenance

Operational maintenance for pgvector indexes:

1. Run `ANALYZE embedding_records` after large embedding imports or re-embedding.
2. Reindex HNSW indexes after bulk invalidation/rebuild cycles:
   `REINDEX INDEX CONCURRENTLY idx_embedding_records_hnsw_model_active`.
3. Keep only one active embedding per `(chunk_id, model_configuration_id)`.
   Older embeddings should be marked `invalidated`, not deleted, until audit
   retention policy permits removal.
4. When model name, provider, dimension, or revision changes, create a new
   `model_configurations` row and write new `embedding_records`; do not reuse
   the prior embedding space.
5. Monitor timeout and empty-result rates per model configuration to detect
   index drift, disabled providers, or license-policy invalidation.

## Limitations

The current service returns structured search results and score components.
Persisted `retrieval_runs` and `retrieval_results` traces are completed by the
hybrid retrieval task that combines exact, full-text, vector, and reranker scores.
