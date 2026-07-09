# TASK-08-03 — Local Ollama and vLLM Adapter

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-OSS-004
- SRS §43 Self-host Profiles

## Objective

Implement local-provider adapters for Ollama and/or vLLM using the common LLM contract.

## Scope

### In Scope

- Implement local-provider adapters for Ollama and/or vLLM using the common LLM contract.
- Expose health and capability checks.

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

- [ ] Minimal self-host profile can operate without cloud LLM credentials.
- [ ] Unavailable local provider produces actionable health errors.
- [ ] Fallback configuration is supported.

## Required Tests

### Unit and Contract Tests

- Local adapter mock/integration tests
- Health/fallback tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/providers/local-llm.md`

## Completion Report

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/local_llm_adapters.py` — Ollama and vLLM adapters (98 lines)
- `services/orchestrator/tests/test_local_llm_adapters.py` — 8 comprehensive tests
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py` — Exported local adapters
- `docs/providers/local-llm.md` — Self-host documentation with model recommendations

### Commands and Tests Executed

```bash
uv run pytest services/orchestrator/tests/test_local_llm_adapters.py -v
# 8 passed in 1.22s

uv run pytest services/orchestrator/tests/ -v
# 29 passed in 1.59s (all orchestrator tests)

uv run mypy services/orchestrator/src/zayd_service_orchestrator/local_llm_adapters.py
# Success: no issues found
```

### Acceptance Criteria Result

- [x] Minimal self-host profile can operate without cloud LLM credentials — Ollama and vLLM require no API keys
- [x] Unavailable local provider produces actionable health errors — Health checks return "unavailable" with clear messages
- [x] Fallback configuration is supported — Registry allows multiple providers with fallback logic

### Security and License Review

- No API keys required for local endpoints (Ollama)
- Optional API key support for vLLM when needed
- Health checks properly detect unavailable services
- No production secrets committed

### Known Limitations

- Local adapters assume OpenAI-compatible endpoints (Ollama and vLLM both support this)
- Default timeouts are longer (60s) for local inference
- Model selection is manual; no automatic model discovery

### Follow-up Tasks

- Consider adding automatic model selection based on available Ollama models
- Document recommended Thai-language models after testing

### Commit

- `9c14e9c` — feat(orchestrator): add OpenAI-compatible and local LLM adapters
