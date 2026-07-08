# Hybrid Search

Status: implemented for TASK-07-05.

Hybrid retrieval combines exact-reference, full-text, vector similarity, and
source-reliability signals into one deterministic ranking. It composes the
published-only retrieval services introduced by TASK-07-03 and TASK-07-04.

## Query Contract

`HybridSearchService` accepts:

- query text and query language
- optional embedding, model configuration, provider, and vector timeout
- metadata filters for madhhab, source type, license status, source language,
  and minimum reliability
- pagination
- optional request and trace IDs
- versioned score weights

The vector signal is optional. If an embedding is supplied, a
`model_configuration_id` is required. If either side is missing, the service
fails closed with `HYBRID_VECTOR_SIGNAL_INCOMPLETE`.

## Visibility Gates

Hybrid search does not bypass lower-level retrieval filters. Full-text and vector
candidate sets are produced by services that enforce, in SQL:

- published document and document version state
- published chunk state
- active source
- eligible license status
- allowed embedding permission
- active embedding space for vector results

Hybrid ranking only merges candidates returned by those fail-closed services.

## Score Components

Each result records:

- `score_exact`
- `score_full_text`
- `score_vector`
- `score_reliability`
- `score_final`

Exact and full-text scores are normalized against the maximum score in the
candidate set. Vector cosine similarity is mapped from `[-1, 1]` to `[0, 1]`.
Reliability is normalized from source reliability level `1..5` to `[0.2, 1.0]`.
Missing optional signals score as zero for that component and remain visible in
result metadata.

## Versioned Weights

Weights are represented by `HybridSearchWeights` and default to:

```text
version = hybrid-weights-v1
exact = 0.35
full_text = 0.25
vector = 0.30
reliability = 0.10
```

The service normalizes supplied weights so callers may configure relative
weights without pre-summing to one. Negative weights, all-zero weights, and empty
weight versions are rejected with stable errors.

## Determinism

For fixed inputs and weight version, ordering is deterministic:

1. final hybrid score
2. exact score
3. full-text score
4. vector score
5. canonical reference
6. chunk ID

This protects regression fixtures from nondeterministic database ordering when
multiple chunks have equal component scores.

## Trace Persistence

When `persist_run` is enabled, the service writes:

- one `retrieval_runs` row with request ID, trace ID, normalized query, filters,
  retriever version, and evidence flag
- one `retrieval_results` row per returned result with rank and all score
  components
- metadata containing weight version, normalized weights, signal sources,
  original component scores, normalization framework version, and vector
  embedding-space metadata when used

The current implementation records only returned, paginated results. Future
evaluation tooling may persist candidate sets separately if deeper offline
analysis requires it.
