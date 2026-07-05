# TASK-04-03 — License Policy Engine

## Status

`TODO`

## Model Tier

Tier S

## Related Requirements

- FR-EXT-002
- FR-EXT-004
- SRS §15 License Registry

## Objective

Implement deterministic decisions for persistent storage, caching TTL, embedding, commercial use, redistribution and attribution.

## Scope

### In Scope

- Implement deterministic decisions for persistent storage, caching TTL, embedding, commercial use, redistribution and attribution.
- Expose a policy decision API for ingestion, retrieval and export workflows.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-04-02

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

- [ ] LLMs cannot override license decisions.
- [ ] Every decision includes reason codes and source license version.
- [ ] Boundary cases for expiry, unknown rights and cache-only content are covered.

## Required Tests

### Unit and Contract Tests

- Policy decision-table tests
- Expiry and conflict tests
- Property-based tests for forbidden combinations

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/license-policy-engine.md`

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
