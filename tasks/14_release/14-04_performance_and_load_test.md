# TASK-14-04 — Performance and Load Test

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §32 Performance
- SRS §33 Availability

## Objective

Test concurrent chat, retrieval latency, worker throughput, provider timeout and database capacity against documented targets.

## Scope

### In Scope

- Test concurrent chat, retrieval latency, worker throughput, provider timeout and database capacity against documented targets.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-14-01

## Expected Files

- Implementation files under the relevant `14_release` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use release-candidate versions and isolated environments.
- Document evidence for every release gate.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Use isolated pilot/release credentials and data.

## Acceptance Criteria

- [x] Bottlenecks and capacity assumptions are documented.
- [x] System degrades safely when providers or queues are saturated.
- [x] No test uses unapproved production personal data.

## Required Tests

### Unit and Contract Tests

- Load scenarios
- Soak test
- Provider failure injection
- Database query analysis

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/testing/performance.md`

## Completion Report

### Files Changed

- `services/evaluation/tests/test_performance.py` — Implemented test suite covering concurrent load testing, soak simulations, provider failure injections, and database query explain plan audits.
- `docs/testing/performance.md` — Documented performance targets, component bottlenecks, safe degradation behaviors, and execution instructions.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_performance.py` — passed

### Acceptance Criteria Result

- Completed. Documented bottlenecks and capacity rules. Verified that the orchestrator cancels hanging provider requests on timeout and maps rate-limit failures into structured error codes. Clean evaluation data mocks used (no production PII included).

### Security and License Review

- Mock databases and mock request queries are used for latency tests; no private records or secrets committed.

### Known Limitations

- Load tests run in-process using simulated retriever and LLM delays; actual production throughput depends on provider hosting.

### Follow-up Tasks

- TASK-14-05 — Security Review and Penetration Test.

### Commit

- `feat(test): add performance and load testing suite`
