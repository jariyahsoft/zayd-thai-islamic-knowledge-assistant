# Retrieval Metrics

`RetrievalMetricsService` calculates Recall@5, Recall@10, MRR, precision, and metadata-filter
correctness from persisted `retrieval_only` and `citation` benchmark results. A case may declare
multiple acceptable source IDs; any acceptable source counts for recall and reciprocal rank.

Observed and expected source references are parsed as UUIDs. Invalid references are counted in the
report, and cases without valid expected references are counted explicitly instead of being treated
as successful retrieval. Metric output groups the same calculations by `topic`, `language`, and
`madhhab` provenance, defaulting missing values to `unknown`.

Calculating metrics with an actor records the versioned aggregate in the benchmark run and writes a
privacy-safe audit record containing counts only. It requires `evaluations.read`; no questions,
source text, expected answers, or retrieval payloads appear in the aggregate.
