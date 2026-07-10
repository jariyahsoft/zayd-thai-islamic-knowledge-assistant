# TASK-12-03 — Retrieval Metrics

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §17.2 Metrics

## Objective

Calculate Recall@5, Recall@10, MRR, precision and metadata-filter correctness.

## Scope

### In Scope

- Calculate Recall@5, Recall@10, MRR, precision and metadata-filter correctness.

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

- [x] Metrics handle multiple acceptable sources.
- [x] Missing/invalid references are reported explicitly.
- [x] Results can be grouped by topic, language and madhhab.

## Required Tests

### Unit and Contract Tests

- Metric unit tests with hand-calculated fixtures
- Grouping/export tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/evaluation/retrieval-metrics.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/evaluation/src/zayd_service_evaluation/retrieval_metrics.py`, evaluation exports/tests, `docs/evaluation/retrieval-metrics.md`, and task records.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_retrieval_metrics.py -q` — 3 passed; focused Ruff and MyPy passed. Broader evaluation regression checks passed.

### Acceptance Criteria Result

- Passed. Hand-calculated metrics cover multiple accepted sources, invalid observed references, missing expected references, metadata filters, and provenance grouping.

### Security and License Review

- Read permission is required. Persisted run aggregates and audit records contain counts/version only, never question text, expected answers, or source bodies.

### Known Limitations

- Metrics consume executor-provided retrieved source IDs; live retrieval adapter conformance remains a later integration concern.

### Follow-up Tasks

- TASK-12-07 Evaluation Dashboard.

### Commit

- Pending focused commit.
