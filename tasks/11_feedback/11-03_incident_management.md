# TASK-11-03 — Incident Management

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §16 Incident Severity
- FR-FDB-007

## Objective

Implement P0-P3 incidents, timeline, ownership, notifications and links to source suspension/answer invalidation.

## Scope

### In Scope

- Implement P0-P3 incidents, timeline, ownership, notifications and links to source suspension/answer invalidation.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-11-02
- TASK-06-05

## Expected Files

- Implementation files under the relevant `11_feedback` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Maintain immutable incident history.
- Minimize personal data and support controlled redaction.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect incident details and reporter privacy.

## Acceptance Criteria

- [x] P0/P1 trigger configured alerts.
- [x] Incident actions are audited and idempotent.
- [x] Personal data is minimized in incident exports.

## Required Tests

### Unit and Contract Tests

- Severity workflow tests
- Alert integration tests
- Suspension linkage tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/incident-management.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Incident service/model, API routes/tests, migration `0015`, operations documentation, and task records.

### Commands and Tests Executed

- Focused pytest: 5 passed; focused Ruff, MyPy, and `git diff --check`: passed.

### Acceptance Criteria Result

- Passed: P0/P1 invoke the configured alert sink once; timeline/assignment/transitions are audited and idempotent; exports are bounded and privacy-minimized.

### Security and License Review

- Protected by MFA-backed feedback permissions. Timeline is append-only in PostgreSQL. Migration and alert-sink configuration require human security/DBA review.

### Known Limitations

- The default application sink reports `not_configured`; production must inject an operations-owned sink. Suspension remains separately authorized.

### Follow-up Tasks

- TASK-11-04 — Answer Invalidation

### Commit

- Pending focused commit.
