# Full-text Search

TASK-07-03 introduces exact-reference and full-text retrieval over published chunks.

## Retrieval Scope

The full-text search service only returns chunks that satisfy all production retrieval gates:

- `document_chunks.is_published = true`
- `documents.review_status = published`
- `document_versions.status = published`
- `document_versions.frozen_at IS NOT NULL`
- active source
- eligible retrieval license status
- embedding permission allowed

This keeps search visibility aligned with the review, publish, suspend, and rollback workflows already enforced elsewhere in the system.

## Query Behavior

`FullTextSearchService` accepts:

- free-text query
- query language
- optional `madhhab`
- optional `source_type`
- optional `license_status`
- optional `source_language`
- optional minimum reliability level
- pagination via `limit` and `offset`

Queries are normalized with the existing Thai/Arabic normalization framework before scoring.

## Scoring

Deterministic exact reference handling comes first:

1. exact canonical reference match
2. canonical reference prefix match
3. normalized content substring match
4. normalized term-hit fallback

Results return:

- `score_exact`
- `score_full_text`
- `score_final`
- retrieval rank

This matches the SRS requirement that score components remain explainable and that exact references receive deterministic handling.

## PostgreSQL Path

The service currently exposes the intended PostgreSQL statement shape and a migration that adds the relevant indexes:

- `reference` lookup index for exact canonical references
- trigram GIN index on `content_normalized`
- `to_tsvector('simple', content_normalized)` GIN index
- supporting filter indexes on published documents, versions, and licenses

The PostgreSQL query path uses:

- `to_tsvector('simple', content_normalized)`
- `websearch_to_tsquery('simple', <normalized query>)`
- exact and prefix reference checks

SQLite-backed tests still verify the functional visibility and scoring rules so the repository test suite remains lightweight.

## Output and Traceability

Each result includes:

- chunk ID
- document version ID
- document ID
- source ID
- canonical reference
- original and normalized content
- language
- madhhab
- source type
- license status
- score components
- rank
- metadata describing backend, reliability, and chunking strategy version

The retriever version is `full-text-retriever-v1`.
