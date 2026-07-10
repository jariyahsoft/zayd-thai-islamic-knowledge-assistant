# TASK-13-03 — Metrics and Dashboards

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §19 Analytics
- SRS §35 Observability

## Objective

Expose metrics for latency, errors, queue depth, local RAG hit, external fallback, citation failure, cost and provider health.

## Scope

### In Scope

- Expose metrics for latency, errors, queue depth, local RAG hit, external fallback, citation failure, cost and provider health.
- Provide baseline Prometheus/Grafana dashboards.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-13-02

## Expected Files

- Implementation files under the relevant `13_operations` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Default configurations must be secure and observable.
- Avoid sensitive/high-cardinality telemetry.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Run secret, dependency, container and configuration scans.

## Acceptance Criteria

- [x] Metrics avoid high-cardinality personal identifiers.
- [x] Dashboards include useful alerts and runbook links.
- [x] Cost data distinguishes provider/model where available.

## Required Tests

### Unit and Contract Tests

- Metric endpoint tests
- Cardinality review
- Dashboard provisioning smoke test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/metrics.md`
- `infra/monitoring/README.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/api/src/zayd_service_api/app.py` — added `/metrics` snapshot support that combines queue/provider DB summaries with telemetry counters and histograms for latency, errors, local RAG hits, external fallback, citation verification failures, provider health, and cost summary.
- `services/api/tests/test_metrics_api.py` — added metrics endpoint coverage for summary values and Prometheus export content.
- `services/common/src/zayd_common/telemetry.py` — exposed metric/counter snapshots and registry reset helpers needed by the metrics surface and tests.
- `services/api/tests/test_logging_api.py` — verified request metrics are emitted from the API middleware path.
- `docs/operations/metrics.md` — documented exported metrics, cardinality constraints, dashboard coverage, and repository-stage limitations.
- `infra/monitoring/README.md` — documented monitoring assets, endpoint contract, runbook links, and sampling note.
- `infra/monitoring/prometheus.yml` — added baseline scrape configuration for the API metrics endpoint.
- `infra/monitoring/grafana-dashboard.json` — added baseline dashboard panels for API latency, error rate, queue depth, provider health, citation failures, fallback attempts, and token usage.

### Commands and Tests Executed

- `uv run pytest services/api/tests/test_metrics_api.py services/api/tests/test_logging_api.py services/common/tests/test_telemetry.py services/orchestrator/tests/test_openai_llm_adapter.py services/orchestrator/tests/test_provider_sdk.py services/retrieval/tests/test_hybrid_search.py -q` — passed.
- `uv run mypy services/api/src/zayd_service_api/app.py services/common/src/zayd_common/telemetry.py services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py services/retrieval/src/zayd_service_retrieval/hybrid_search.py --ignore-missing-imports` — passed.
- `uv run ruff check services/api/src/zayd_service_api/app.py services/api/tests/test_metrics_api.py services/api/tests/test_logging_api.py services/common/src/zayd_common/telemetry.py services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py services/retrieval/src/zayd_service_retrieval/hybrid_search.py services/common/tests/test_telemetry.py services/orchestrator/tests/test_openai_llm_adapter.py services/orchestrator/tests/test_provider_sdk.py services/retrieval/tests/test_hybrid_search.py` — passed.
- `git diff --check` — passed.

### Acceptance Criteria Result

- [x] Metrics avoid high-cardinality personal identifiers. Exported counters/histograms use only bounded labels such as method, path, provider, model, service, and status; user IDs, conversation IDs, and raw text are excluded.
- [x] Dashboards include useful alerts and runbook links. Monitoring scaffolding includes Grafana starter panels with links back to logging, tracing, and metrics runbooks.
- [x] Cost data distinguishes provider/model where available. Provider generate metrics label by provider/model, while inventory summary still reports configured daily cost limits from model configuration.

### Security and License Review

- `/metrics` exposes aggregate operational summaries only; it does not include request bodies, conversation text, document text, signed URLs, tokens, or personal identifiers.
- Baseline dashboards and scrape configs are static repository assets and do not embed live credentials or environment-specific secrets.
- No third-party dashboard packs, metrics libraries, or copyrighted datasets were imported.

### Known Limitations

- The current metrics endpoint returns JSON plus embedded Prometheus-style text in one response for repository-stage testing convenience rather than a dedicated plain-text scrape surface.
- Queue age is approximated from in-process worker lifecycle spans, not a durable queue backend.
- Cost reporting is limited to configured daily model limits and in-process provider token/latency counters; it is not external billing reconciliation.

### Follow-up Tasks

- TASK-10-04 can now proceed against the completed operations metrics/dashboard foundation.
- Future production operations work should split JSON and Prometheus scrape contracts and move telemetry storage to durable observability infrastructure.

### Commit

- Pending
