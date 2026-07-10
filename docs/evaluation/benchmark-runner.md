# Benchmark Runner

`BenchmarkRunner` executes a pinned dataset version against explicit model, provider, prompt,
policy, retriever, embedding, and reranker versions. Every run records the Git commit, random seed,
runner version, and arbitrary non-sensitive environment metadata. The same dataset/configuration and
seed produce the same case order and random stream.

Executors implement the typed `BenchmarkExecutor` contract. An exception affects only its current
case and is stored as a sanitized exception class, never a raw stack trace or private payload. The
runner persists one result per case and completes the remaining cases.

Reports are available as deterministic JSON, CSV, and Markdown. Full exports require
`evaluations.read`. Public exports may be produced without private permission but include only
approved public cases; questions, expected answers, source text, executor output, prompts, and
private cases are excluded from report rows.

The runner is provider-independent and works with local/mock executors. Production adapters must
apply the same provider egress, secret, timeout, and privacy controls as answer orchestration.

Runtime implementation: `services/evaluation/src/zayd_service_evaluation/runner.py`.
