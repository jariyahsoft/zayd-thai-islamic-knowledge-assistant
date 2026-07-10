# TASK-11-04 — Answer Invalidation

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-CIT-009
- FR-CIT-010

## Objective

Mark answers invalid with reason, notify affected views and discover other answers using the same invalid citation/source.

## Scope

### In Scope

- Mark answers invalid with reason, notify affected views and discover other answers using the same invalid citation/source.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-11-03
- TASK-08-07

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

- [x] New views show warnings immediately.
- [x] Historical record is preserved.
- [x] Bulk discovery is bounded, retryable and auditable.

## Required Tests

### Unit and Contract Tests

- Invalidation E2E
- Affected-answer query tests
- Notification tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/answer-invalidation.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Answer invalidation service/model/API/tests, migration `0016`, operations docs, and task records.

### Commands and Tests Executed

- Focused pytest: 5 passed. Broader citation/lifecycle/saved-answer/API regression suite passed. Focused Ruff, MyPy, and `git diff --check` passed.

### Acceptance Criteria Result

- Passed: warnings are persisted immediately; append-only records preserve the reason and linkage; citation/source discovery is capped at 200, pageable, retryable, and audited.

### Security and License Review

- MFA-backed `answers.invalidate`/`answers.review` permissions are enforced. Notification/audit payloads omit answer and conversation bodies. Migration needs human security/DBA review.

### Known Limitations

- Production must configure the notification sink. Discovery uses offset pagination; very large changing result sets may later benefit from snapshot cursors.

### Follow-up Tasks

- TASK-11-05 — Convert Incident to Regression Test

### Commit

- Pending focused commit.
