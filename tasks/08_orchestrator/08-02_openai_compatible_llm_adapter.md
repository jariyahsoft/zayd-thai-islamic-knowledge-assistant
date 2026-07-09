# TASK-08-02 — OpenAI-compatible LLM Adapter

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §9.1 LLM Provider Interface
- FR-OSS-004

## Objective

Implement configurable base URL, model selection, streaming, structured outputs, timeout, retry and usage accounting for OpenAI-compatible APIs.

## Scope

### In Scope

- Implement configurable base URL, model selection, streaming, structured outputs, timeout, retry and usage accounting for OpenAI-compatible APIs.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-01

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

- [ ] No provider-specific assumptions leak into orchestrator code.
- [ ] Secrets are masked.
- [ ] Streaming cancellation and malformed structured responses are handled.

## Required Tests

### Unit and Contract Tests

- Adapter integration tests with mock server
- Streaming cancellation test
- Structured-output validation tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/providers/openai-compatible.md`

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
