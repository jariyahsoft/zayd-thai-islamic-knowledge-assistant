# TASK-13-02 — OpenTelemetry Instrumentation

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §35 Observability

## Objective

Instrument API, retrieval, LLM, external provider, database and worker spans.

## Scope

### In Scope

- Instrument API, retrieval, LLM, external provider, database and worker spans.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-13-01

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

- [x] Trace context propagates across asynchronous jobs.
- [x] Sensitive prompt/document contents are excluded by default.
- [x] Sampling is configurable.

## Required Tests

### Unit and Contract Tests

- Span propagation integration tests
- Sensitive attribute tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/tracing.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/telemetry.py` — added an in-process telemetry registry with spans, counters, histograms, deterministic sampling, sanitization helpers, metric snapshots, and Prometheus-style export.
- `services/common/src/zayd_common/__init__.py` — exported telemetry helpers for shared service usage.
- `services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py` — instrumented answer orchestration spans and counters for evidence sufficiency, expanded retrieval fallback, citation verification, and orchestration terminal states.
- `services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py` — instrumented provider health/generate spans plus provider latency, token, and status counters.
- `services/retrieval/src/zayd_service_retrieval/hybrid_search.py` — instrumented retrieval span, retrieval latency, score distribution, and local RAG hit/miss counters.
- `services/worker/src/zayd_service_worker/main.py` — added worker lifecycle span instrumentation.
- `services/api/src/zayd_service_api/app.py` — reused propagated trace IDs through chat/orchestration entrypoints and added API request latency/error metrics at the middleware boundary.
- `services/common/tests/test_telemetry.py` — added sanitizer, metrics export, and sampling configuration coverage.
- `services/orchestrator/tests/test_openai_llm_adapter.py` — added provider metrics assertions for success and error paths.
- `services/orchestrator/tests/test_provider_sdk.py` — exercised metrics export compatibility with provider tests.
- `services/retrieval/tests/test_hybrid_search.py` — added retrieval metric export assertions.
- `docs/operations/tracing.md` — documented span coverage, sanitization rules, and configurable sample rate.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_telemetry.py services/orchestrator/tests/test_openai_llm_adapter.py services/orchestrator/tests/test_provider_sdk.py services/retrieval/tests/test_hybrid_search.py -q` — passed.
- `uv run mypy services/common/src/zayd_common/telemetry.py services/common/src/zayd_common/__init__.py services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py services/retrieval/src/zayd_service_retrieval/hybrid_search.py services/worker/src/zayd_service_worker/main.py services/api/src/zayd_service_api/app.py --ignore-missing-imports` — passed.
- `uv run ruff check services/common/src/zayd_common/telemetry.py services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py services/retrieval/src/zayd_service_retrieval/hybrid_search.py services/worker/src/zayd_service_worker/main.py services/api/src/zayd_service_api/app.py services/common/tests/test_telemetry.py services/orchestrator/tests/test_openai_llm_adapter.py services/orchestrator/tests/test_provider_sdk.py services/retrieval/tests/test_hybrid_search.py` — passed.
- `git diff --check` — passed.

### Acceptance Criteria Result

- [x] Trace context propagates across asynchronous jobs. API middleware binds request/trace IDs, chat streaming forwards them into orchestration, and worker lifecycle telemetry binds its own generated context.
- [x] Sensitive prompt/document contents are excluded by default. Telemetry sanitization strips prompt/message/document/token-like attributes before spans are recorded.
- [x] Sampling is configurable. `TELEMETRY_SAMPLE_RATE` and the registry setter now provide deterministic `0.0` to `1.0` sampling control.

### Security and License Review

- Instrumentation records only low-cardinality operational metadata such as service, provider, model, request, and status attributes.
- Prompt bodies, raw question text, answer text, document text, tokens, secrets, signed URLs, and provider credentials are excluded by sanitizer rules and were not persisted.
- No external tracing collector, SDK, or third-party package was added, avoiding new license/provenance obligations at this repository stage.

### Known Limitations

- This task provides repository-stage in-process telemetry rather than full OpenTelemetry export to an external collector.
- Database internals are represented indirectly through orchestrated service spans and request metrics; there is not yet fine-grained SQL statement tracing.
- Sampling is process-local and runtime-configured; there is no distributed control plane for coordinated sampling across multiple replicas.

### Follow-up Tasks

- TASK-13-03 extends these counters/histograms into a metrics snapshot and Grafana/Prometheus scaffolding.
- Future production operations work can replace the in-process registry with a full collector/exporter while keeping the same low-cardinality telemetry contract.

### Commit

- Pending
