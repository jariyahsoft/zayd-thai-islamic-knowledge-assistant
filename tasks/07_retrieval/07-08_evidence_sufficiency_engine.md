# TASK-07-08 — Evidence Sufficiency Engine

## Status

`TODO`

## Model Tier

Tier S

## Related Requirements

- FR-RET-012
- FR-RET-014
- SRS §27 Evidence Sufficiency

## Objective

Implement deterministic sufficiency rules using result count, scores, source approval, madhhab consistency, citation completeness and conflict signals.

## Scope

### In Scope

- Implement deterministic sufficiency rules using result count, scores, source approval, madhhab consistency, citation completeness and conflict signals.
- Optionally support an LLM evaluator as a non-authoritative secondary signal.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-06
- TASK-07-07

## Expected Files

- Implementation files under the relevant `07_retrieval` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Record retrieval configuration and model/index versions.
- Enforce status/license filters inside data-access queries, not after retrieval.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Do not allow filters to be bypassed through query expansion or provider fallback.

## Acceptance Criteria

- [ ] Returns SUFFICIENT, PARTIALLY_SUFFICIENT, INSUFFICIENT or CONFLICTING with reason codes.
- [ ] Insufficient evidence cannot silently proceed as high-confidence answer.
- [ ] Rules and thresholds are versioned.

## Required Tests

### Unit and Contract Tests

- Decision-table tests
- Conflicting-source cases
- Threshold regression tests
- LLM evaluator failure tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/evidence-sufficiency.md`

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
