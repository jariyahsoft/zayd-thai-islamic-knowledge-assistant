# Citation Metrics

Citation metrics consume the deterministic machine-readable output from
`citation-verification-v1`; they do not ask a model to re-grade claims. The report includes citation
correctness, expected-citation completeness, fabricated citation rate, and claim support rate.

Failure counters distinguish:

- nonexistent or malformed citation tokens;
- existing citations whose declared reference is wrong;
- unsupported, partial, unverifiable, or invalid-citation claims;
- cases missing one or more expected citations;
- malformed metric inputs.

Human-review overrides are returned only to callers with `evaluations.read` and retain case key,
claim ID, reviewer ID, decision, reason code, and timestamp. Persisted run aggregates and audit logs
store override counts—not reviewer identities or case content. Overrides remain trace metadata and
do not silently upgrade deterministic metric outcomes.

Metrics are versioned as `citation-metrics-v1` and may be persisted into the benchmark run with a
privacy-safe audit record.
