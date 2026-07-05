# TASK-04-01 — Source Registry API

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- SRS §23.2 Source
- FR-ADM-006

## Objective

Implement create, read, update, suspend and search operations for knowledge sources.

## Scope

### In Scope

- Implement create, read, update, suspend and search operations for knowledge sources.
- Capture ownership, language, country, source type, reliability level and active status.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-03 complete

## Expected Files

- Implementation files under the relevant `04_data_governance` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Policy decisions must be deterministic and versioned.
- Keep permission evidence private and access controlled.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- A missing or ambiguous license must block restricted operations.

## Acceptance Criteria

- [ ] Inactive sources cannot be assigned to new documents.
- [ ] Suspension is audited and visible to downstream services.
- [ ] Search supports pagination and structured filters.

## Required Tests

### Unit and Contract Tests

- Source CRUD tests
- Suspension behavior tests
- RBAC tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/sources.md`
- `docs/governance/source-policy.md`

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
