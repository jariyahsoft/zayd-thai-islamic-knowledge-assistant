# TASK-08-08 — Citation Verification Engine

## Status

`TODO`

## Model Tier

Tier S

## Related Requirements

- FR-CIT-003
- FR-CIT-004
- FR-ANS-008

## Objective

Verify citation existence, reference correctness, quoted-text fidelity, claim support and madhhab consistency using deterministic checks before optional model evaluation.

## Scope

### In Scope

- Verify citation existence, reference correctness, quoted-text fidelity, claim support and madhhab consistency using deterministic checks before optional model evaluation.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-06
- TASK-08-07

## Expected Files

- Implementation files under the relevant `08_orchestrator` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use typed provider contracts and structured outputs.
- Store only safe traces; never persist hidden chain-of-thought.
- Apply deterministic policy and verification before model judgement.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Prevent prompt injection and citation fabrication.

## Acceptance Criteria

- [ ] Failed verification triggers revision or abstention.
- [ ] Every cited claim has a machine-readable verification result.
- [ ] Verifier cannot retrieve unpublished or invalidated evidence as valid.

## Required Tests

### Unit and Contract Tests

- Quote/reference exactness tests
- Claim-support benchmark fixtures
- Invalidated citation tests
- Revision path E2E

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/citation-verification.md`

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
