# TASK-12-01 — Evaluation Data Schema

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §17 Evaluation
- SRS §36 Testing

## Objective

Define versioned schemas for multiple choice, open-ended, retrieval-only, citation, abstention and risk-routing cases.

## Scope

### In Scope

- Define versioned schemas for multiple choice, open-ended, retrieval-only, citation, abstention and risk-routing cases.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-02 complete

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

- [x] Cases include sources, license metadata, reviewer status and expected behavior.
- [x] Public and private test-set visibility is supported.
- [x] Schema validation is deterministic.

## Required Tests

### Unit and Contract Tests

- Schema fixture tests
- Migration/compatibility tests
- Visibility/permission tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/evaluation/data-schema.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Evaluation schema/store, SQLAlchemy models and RBAC, migration `0017`, tests, documentation, and task records.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_evaluation_schema.py database/tests/test_evaluation_schema_migration.py -q` — 6 passed. Focused Ruff and MyPy passed; `git diff --check` passed.

### Acceptance Criteria Result

- Passed. All six case types validate deterministically; cases persist source/license/reviewer/expected behavior metadata; private visibility is permission-gated and public cases require approval plus redistributable sources.

### Security and License Review

- Evaluation-specific read/manage permissions are MFA-backed at API boundaries. Public validation fails closed on approval/license status. Migration requires human DBA/security review; case content requires human religious-content review before approval.

### Known Limitations

- No real benchmark content or golden religious answers were introduced. Dataset publication workflow remains a later task.

### Follow-up Tasks

- TASK-12-02 Benchmark Runner; TASK-12-06 starter set; unblock TASK-11-05 only after EPIC-12 is complete.

### Commit

- Pending focused commit.
