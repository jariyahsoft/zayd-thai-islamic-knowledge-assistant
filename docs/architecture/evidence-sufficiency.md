# Evidence Sufficiency

Status: implemented for TASK-07-08.

Evidence sufficiency is a deterministic gate between retrieval and answer
generation. It evaluates whether retrieved evidence is strong enough to answer,
needs more search, requires conflict handling, or must abstain.

## Outputs

The service returns one of the canonical `EvidenceStatus` values:

- `SUFFICIENT`
- `PARTIALLY_SUFFICIENT`
- `INSUFFICIENT`
- `CONFLICTING`

Every decision includes reason codes, thresholds version, score summary, source
counts, high-confidence permission, search-more/abstain flags, and a structured
trace.

## Rule Inputs

`EvidenceSufficiencyService` considers:

- result count
- distinct source count
- final retrieval/reranker score
- average score
- source reliability
- requested madhhab consistency
- citation completeness
- license eligibility
- explicit conflict signals
- conflicting stances in the same conflict group

The engine never relies on one similarity score alone.

## Versioned Thresholds

Rules are configured by `EvidenceSufficiencyThresholds` and versioned by
`evidence-sufficiency-rules-v1`.

Defaults:

```text
min_sufficient_results = 2
min_partial_results = 1
min_sufficient_top_score = 0.70
min_partial_top_score = 0.45
min_sufficient_average_score = 0.55
min_reliability_score = 0.60
min_distinct_sources = 1
require_citations = true
```

Invalid thresholds fail closed with stable errors.

## Decision Behavior

- No candidates or scores below the partial threshold produce `INSUFFICIENT`.
- Explicit conflict signals or conflicting stances produce `CONFLICTING`.
- Missing citations, low reliability, madhhab mismatch, low average score, or
  too few sufficient results produce `PARTIALLY_SUFFICIENT`.
- Only passing all deterministic rules produces `SUFFICIENT`.

`INSUFFICIENT` sets `should_abstain = true` and
`allow_high_confidence_answer = false`. `PARTIALLY_SUFFICIENT` sets
`should_search_more = true`. `CONFLICTING` requires conflict handling and also
blocks high-confidence answer generation.

## LLM Evaluator

An optional LLM evaluator can be attached as a secondary signal. It is never
authoritative. If the evaluator fails, the rule-based decision still completes
and records `LLM_EVALUATOR_FAILED` in the trace.

## Retrieval Trace Persistence

When a `retrieval_run_id` and unit of work are supplied, the service updates the
matching `retrieval_runs.evidence_sufficient` flag and records the sufficiency
trace under `filters.evidence_sufficiency`.

This keeps answer orchestration from silently treating insufficient evidence as
high-confidence evidence.
