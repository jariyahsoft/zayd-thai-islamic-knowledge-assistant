# Embedding Providers

TASK-07-02 introduces a versioned embedding provider interface that works in fully local mode and with OpenAI-compatible embedding APIs.

## Provider Contract

The shared interface lives in `zayd_common.embeddings` and exposes:

- `embed_documents(texts, *, language, normalize=True)`
- `embed_query(text, *, language, normalize=True)`
- `provider_info()`

Every provider reports:

- provider name and provider version
- interface version
- model ID and optional revision
- embedding dimensions
- whether normalization is enabled
- normalization framework version
- batch size
- timeout seconds
- max retries

The high-level `EmbeddingService` validates dimensions on every response so mismatches are detected before vectors are written or searched.

## Local Mode

`LocalHashEmbeddingProvider` is the default self-hosted implementation. It produces deterministic normalized vectors without any network dependency and satisfies `FR-OSS-004` so the repository can run without proprietary services.

Characteristics:

- deterministic local hashing over normalized tokens
- multilingual-safe fallback for Thai, Arabic, and generic text
- default dimensions: `128`
- default model ID: `local-hash-multilingual`
- no external secrets or provider access required

This is a retrieval-safe placeholder until later vector-search work connects real vector persistence and provider-backed re-embedding.

## OpenAI-Compatible Mode

`OpenAICompatibleEmbeddingProvider` targets `/embeddings` endpoints that follow the common OpenAI response shape.

Behavior:

- batches requests by configured batch size
- applies at most one bounded retry by default
- enforces finite timeout
- fails closed on authentication errors, malformed payloads, transport failures, and dimension mismatches

The adapter expects each response row to include:

- `index`
- `embedding`

Rows are re-ordered by `index` before returning.

## Configuration

Relevant environment variables:

- `EMBEDDING_PROVIDER`
- `EMBEDDING_BASE_URL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`
- `EMBEDDING_REVISION`
- `EMBEDDING_DIMENSIONS`
- `EMBEDDING_BATCH_SIZE`
- `EMBEDDING_TIMEOUT_SECONDS`
- `EMBEDDING_MAX_RETRIES`
- `ENABLE_EXTERNAL_PROVIDERS`

Rules:

- `EMBEDDING_PROVIDER=local` works with `ENABLE_EXTERNAL_PROVIDERS=false`
- `EMBEDDING_PROVIDER=openai_compatible` requires `ENABLE_EXTERNAL_PROVIDERS=true`
- OpenAI-compatible mode also requires `EMBEDDING_BASE_URL` and `EMBEDDING_MODEL`
- dimensions, batch size, timeout, and retries must be positive integers

## Testing Expectations

Coverage for TASK-07-02 includes:

- provider contract tests
- deterministic local embedding behavior
- retry handling for OpenAI-compatible batching
- dimension mismatch detection
- runtime configuration validation

The interface is intentionally storage-agnostic. TASK-07-04 will use the same metadata and dimension checks when pgvector indexing is added.
