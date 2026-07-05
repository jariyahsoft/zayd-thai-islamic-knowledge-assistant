# TASK-04-02 — License Registry API

## Status

`TODO`

## Model Tier

Tier S

## Related Requirements

- SRS §15 License Registry
- SRS §23.3 Source License

## Objective

Implement license records covering storage, embedding, commercial use, redistribution, attribution, validity dates and permission evidence.

## Scope

### In Scope

- Implement license records covering storage, embedding, commercial use, redistribution, attribution, validity dates and permission evidence.
- Store permission documents in private object storage.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-04-01

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

- [ ] UNKNOWN, PROHIBITED and EXPIRED licenses cannot authorize publication.
- [ ] Expiry and replacement of license versions are represented without overwriting history.
- [ ] Permission files are access controlled and audited.

## Required Tests

### Unit and Contract Tests

- License CRUD tests
- Expiry tests
- Permission-document access tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/licenses.md`
- `docs/governance/data-licenses.md`

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
