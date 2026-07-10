# TASK-12-04 — Citation Metrics

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §17.2 Metrics
- FR-CIT-004

## Objective

Measure citation correctness, completeness, fabricated citation rate and claim support rate.

## Scope

### In Scope

- Measure citation correctness, completeness, fabricated citation rate and claim support rate.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-12-02

## Expected Files

- Implementation files under the relevant `12_evaluation` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Runs must be reproducible and version-aware.
- Separate public and private evaluation material.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect private benchmark cases and reviewer identity.

## Acceptance Criteria

- [x] Metrics distinguish nonexistent, wrong-reference, unsupported-claim and incomplete-citation failures.
- [x] Human-review overrides are traceable.

## Required Tests

### Unit and Contract Tests

- Metric golden fixtures
- Verifier/metric integration tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/evaluation/citation-metrics.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Citation metrics service/package exports/tests, verifier integration tests, documentation, and task records.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_citation_metrics.py -q` — 3 passed; focused Ruff and MyPy passed. Broader evaluation and citation-verifier regressions passed.

### Acceptance Criteria Result

- Passed. Golden fixtures distinguish all required failure classes and hand-calculated rates. The service consumes real `citation-verification-v1` machine output. Valid human overrides retain reviewer/reason/timestamp traceability.

### Security and License Review

- Requires `evaluations.read`. Stored aggregates/audits omit reviewer identities and case content. Deterministic verifier results remain authoritative; overrides are separately traceable and do not silently change scores.

### Known Limitations

- Override approval policy and UI remain outside this metrics task. Quote-accuracy metrics are not included in this task objective.

### Follow-up Tasks

- TASK-12-07 Evaluation Dashboard.

### Commit

- Pending focused commit.
