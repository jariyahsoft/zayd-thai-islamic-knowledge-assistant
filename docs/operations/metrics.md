# Metrics and Dashboards

Zayd exposes its repository-stage operational snapshot at `GET /admin/dashboard`.
It requires privileged MFA and the server-side `audit.read` permission.

## Scope

The current endpoint provides:

- API request latency and request/error counters
- queue depth summary
- average queue lifecycle age from in-process worker spans
- open feedback count
- provider/model inventory counts
- aggregated configured provider daily cost limits
- local RAG hit/miss counters
- external fallback attempt/improvement counters
- citation verification failure counters
- provider generate latency/token counters
- count of successful provider health checks recorded in memory
- aggregate operational counts only; no raw telemetry export

## Cardinality Rules

Metrics must avoid:

- user IDs
- conversation IDs
- raw question text
- citation body text
- document body text

Only low-cardinality service/provider/model-type style labels should be used.

## Dashboards

Baseline dashboard assets live under `infra/monitoring/` and cover:

1. API health
2. chat and retrieval latency
3. error rate and citation failures
4. queue and feedback depth
5. provider health
6. token/cost configuration summary

## Limitations

- Current telemetry is in-memory and resets on process restart.
- Cost reporting is based on configured daily limits and token usage traces currently available in-process, not external billing reconciliation.
- Direct Prometheus scraping remains disabled until a protected Prometheus-compatible endpoint is provisioned.
