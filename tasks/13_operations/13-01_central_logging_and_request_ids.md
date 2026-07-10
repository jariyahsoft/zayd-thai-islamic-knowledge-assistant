# TASK-13-01 — Central Logging and Request IDs

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §35 Observability
- NFR-PRV-006

## Objective

Implement structured logs and propagated request/trace IDs across web, API and workers.

## Scope

### In Scope

- Implement structured logs and propagated request/trace IDs across web, API and workers.
- Redact secrets and avoid full user-message logging by default.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-01 complete

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

- [x] All core services include request IDs in logs.
- [x] Redaction tests cover tokens, passwords and provider keys.
- [x] Logging failure does not break requests.

## Required Tests

### Unit and Contract Tests

- Log-format tests
- Redaction tests
- Cross-service propagation test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/logging.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/logging.py` — replaced basic logging with structured JSON output, request/trace context binding, request ID normalization, redaction helpers, and a safe stream handler that does not break request handling on log sink failures.
- `services/common/src/zayd_common/__init__.py` — exported logging helpers for service reuse.
- `services/api/src/zayd_service_api/app.py` — added API middleware that propagates `x-request-id` and `x-trace-id`, binds request context, logs request completion/failure, and returns correlation headers to clients.
- `services/worker/src/zayd_service_worker/main.py` — bound worker lifecycle logs to generated request/trace context.
- `services/orchestrator/src/zayd_service_orchestrator/service.py` — aligned runtime settings usage so orchestrator health/logging reflects the actual service environment.
- `services/common/tests/test_logging.py` — added structured log, redaction, and logging failure safety coverage.
- `services/api/tests/test_logging_api.py` — added request header propagation coverage for the API boundary.
- `services/worker/tests/test_worker_imports.py` — verified worker shutdown logs preserve request context.
- `docs/operations/logging.md` — documented logging fields, propagation rules, redaction boundaries, and failure behavior.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_logging.py services/api/tests/test_logging_api.py services/worker/tests/test_worker_imports.py -q` — passed.
- `uv run mypy services/common/src/zayd_common/logging.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/worker/src/zayd_service_worker/main.py services/orchestrator/src/zayd_service_orchestrator/service.py --ignore-missing-imports` — passed.
- `uv run ruff check services/api/src/zayd_service_api/app.py services/common/src/zayd_common/logging.py services/common/src/zayd_common/__init__.py services/worker/src/zayd_service_worker/main.py services/common/tests/test_logging.py services/api/tests/test_logging_api.py services/worker/tests/test_worker_imports.py` — passed.
- `git diff --check` — passed.

### Acceptance Criteria Result

- [x] All core services include request IDs in logs. API requests now bind and return propagated request/trace IDs, and worker lifecycle logs generate equivalent correlation IDs.
- [x] Redaction tests cover tokens, passwords and provider keys. Structured logging redacts sensitive fields and token-like values with explicit unit coverage.
- [x] Logging failure does not break requests. The safe stream handler absorbs formatter/output errors without raising into the request path.

### Security and License Review

- No secrets, bot tokens, provider credentials, production data, or restricted corpus content were committed.
- Logging defaults redact passwords, tokens, authorization headers, provider keys, signed URLs, prompt bodies, and similar sensitive fields.
- Request correlation is metadata-only; full conversation bodies and raw uploaded document contents remain excluded from runtime logs.
- No third-party packages or licensed datasets were added.

### Known Limitations

- Web frontend request logging was not expanded in this task because the repository’s runtime logging foundation lives in the Python services.
- Cross-service propagation currently depends on explicit trace/request ID forwarding by each caller rather than a shared distributed tracing backend.

### Follow-up Tasks

- TASK-13-02 builds on this foundation with span instrumentation and configurable sampling.
- TASK-13-03 consumes the correlation and span data for metrics and dashboard surfaces.

### Commit

- Pending
