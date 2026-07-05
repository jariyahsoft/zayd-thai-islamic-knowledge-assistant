# TASK-13-02 — OpenTelemetry Instrumentation

## Status

`TODO`

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

- [ ] Trace context propagates across asynchronous jobs.
- [ ] Sensitive prompt/document contents are excluded by default.
- [ ] Sampling is configurable.

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

- Pending

### Commands and Tests Executed

- Pending

### Acceptance Criteria Result

- Pending

### Security and License Review

- Pending

### Known Limitations

- Pending

### Follow-up Tasks

- Pending

### Commit

- Pending
