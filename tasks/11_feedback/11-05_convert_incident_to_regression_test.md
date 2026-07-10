# TASK-11-05 — Convert Incident to Regression Test

## Status

`BLOCKED`

## Model Tier

Tier A

## Related Requirements

- FR-FDB-007
- SRS §36 Testing

## Objective

Allow authorized reviewers to create sanitized evaluation cases from confirmed incidents.

## Scope

### In Scope

- Allow authorized reviewers to create sanitized evaluation cases from confirmed incidents.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-11-03
- EPIC-12

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

- [ ] Personal data is redacted before test creation.
- [ ] Expected behavior and source references are required.
- [ ] Created case retains incident provenance without exposing restricted details.

## Required Tests

### Unit and Contract Tests

- Redaction tests
- Evaluation-case creation E2E
- Permission tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/evaluation/incident-regressions.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Task status and execution record only; no product implementation was started.

### Commands and Tests Executed

- Dependency review: TASK-11-03 is complete, but every EPIC-12 task remains `TODO`.

### Acceptance Criteria Result

- Blocked. The evaluation-case schema, benchmark runner, and evaluation workflow required to retain incident provenance do not exist yet.

### Security and License Review

- No security-sensitive implementation was performed. Future work must retain provenance without exposing reporter, answer, conversation, or restricted source data.

### Known Limitations

- Owner action: complete EPIC-12, beginning with TASK-12-01 Evaluation Data Schema and its dependent evaluation workflow, then return TASK-11-05 to `READY`.

### Follow-up Tasks

- EPIC-12 completion.

### Commit

- No commit created; task is blocked by an out-of-range prerequisite.
