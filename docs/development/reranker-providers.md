# Reranker Providers

TASK-07-07 defines a reranker adapter contract with safe fallback to hybrid
ranking.

## Contract

Providers implement:

```text
provider_info() -> RerankerProviderInfo
rerank(request: RerankRequest) -> tuple[RerankScore, ...]
```

`RerankerProviderInfo` records:

- provider name and version
- interface version
- model ID and optional model revision
- timeout and candidate limits
- multilingual capability
- whether provider data sharing is allowed
- whether the provider is external

The interface version is `reranker-interface-v1`.

## Local Provider

`LocalKeywordRerankerProvider` is the default self-hosted provider. It scores
candidate overlap against query terms and does not send query or document text
outside the process.

It is deterministic and intended as a safe baseline until production reranker
plugins are added through the provider SDK.

## Fallback Behavior

`RerankerService` returns hybrid ranking unchanged when:

- reranking is disabled
- the provider raises an error
- provider latency exceeds the configured timeout
- an external provider lacks data-sharing approval

Fallback responses include `fallback_used` and `fallback_reason`. Retrieval does
not fail solely because reranking is unavailable.

## Score Trace

Successful reranking returns:

- `score_reranker`
- final blended score
- reranker provider, model, revision, provider version, and interface version
- provider-specific score metadata

When a `retrieval_run_id` is present and a unit of work is supplied, the service
updates matching `retrieval_results` rows with reranker score, final score,
rank, and model/version metadata.

## Data-Sharing Restrictions

External providers must set `is_external = true`. If
`require_data_sharing_approval` is enabled and provider info reports
`data_sharing_allowed = false`, the service does not call the provider and
falls back to hybrid ranking.

This preserves the product and license boundary that retrieved religious text
must not be sent to external systems without explicit approval.
