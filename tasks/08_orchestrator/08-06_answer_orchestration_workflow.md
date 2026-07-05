# TASK-08-06 — Answer Orchestration Workflow

## Status

`TODO`

## Model Tier

Tier S

## Related Requirements

- FR-ANS-001
- FR-ANS-008
- SRS §6 High-level Architecture

## Objective

Implement a traceable state machine: classify, retrieve, evaluate sufficiency, expand/retrieve, generate, verify, revise/abstain and return.

## Scope

### In Scope

- Implement a traceable state machine: classify, retrieve, evaluate sufficiency, expand/retrieve, generate, verify, revise/abstain and return.
- Add timeout, cancellation and idempotency behavior.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-08
- TASK-08-05

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

- [ ] Every step records status and safe trace metadata.
- [ ] Retries do not create duplicate persisted answers.
- [ ] Cancellation stops provider work where supported.
- [ ] Insufficient/conflicting evidence follows policy.

## Required Tests

### Unit and Contract Tests

- State-machine unit tests
- Timeout/cancellation tests
- End-to-end orchestration fixtures
- Idempotency tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/answer-orchestrator.md`

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
