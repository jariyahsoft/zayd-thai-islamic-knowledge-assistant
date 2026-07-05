# TASK-02-03 — Implement Domain Enums and State Machines

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- SRS §24 Document State Machine
- FR-REV-007
- FR-RET-014

## Objective

Implement typed enums for document status, review decision, storage permission, evidence status, risk level, incident severity and provider status.

## Scope

### In Scope

- Implement typed enums for document status, review decision, storage permission, evidence status, risk level, incident severity and provider status.
- Implement explicit state-transition guards for documents, reviews and incidents.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-02-02

## Expected Files

- Implementation files under the relevant `02_database` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use PostgreSQL-compatible types and explicit constraints.
- Keep domain logic outside migration files.
- Design for versioning and auditability.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect referential integrity and sensitive fields.

## Acceptance Criteria

- [ ] Invalid transitions are rejected with stable error codes.
- [ ] Only PUBLISHED documents are eligible for production retrieval.
- [ ] Every transition records actor, timestamp and reason where required.
- [ ] Unit tests cover allowed and forbidden transitions.

## Required Tests

### Unit and Contract Tests

- Enum serialization tests
- State transition table tests
- Concurrency test for conflicting transitions

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/state-machines.md`

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
