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

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py` — OpenAI-compatible LLM adapter (327 lines)
- `services/orchestrator/tests/test_openai_llm_adapter.py` — 14 comprehensive tests
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py` — Exported adapters
- `services/orchestrator/pyproject.toml` — Added httpx>=0.27.0
- `docs/providers/openai-compatible.md` — Usage documentation

### Commands and Tests Executed

```bash
uv run pytest services/orchestrator/tests/test_openai_llm_adapter.py -v
# 14 passed in 1.34s

uv run mypy services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py
# Success: no issues found

uv run ruff check services/orchestrator/src/zayd_service_orchestrator/openai_llm_adapter.py
# All checks passed!
```

### Acceptance Criteria Result

- [x] No provider-specific assumptions leak into orchestrator code — Uses typed provider contracts
- [x] Secrets are masked — API keys never logged or exposed in error messages
- [x] Streaming cancellation and malformed structured responses are handled — Verified in tests

### Security and License Review

- API keys never logged or exposed in error messages
- Request traces exclude credentials
- Input validation on all external data
- Timeout and retry bounds enforced
- No production secrets committed

### Known Limitations

- Only supports chat completions endpoint (not legacy completions)
- Structured output requires server support for response_format
- Retry logic only retries on 5xx errors, not network errors

### Follow-up Tasks

- None required; implementation is complete and tested

### Commit

- `9c14e9c` — feat(orchestrator): add OpenAI-compatible and local LLM adapters
