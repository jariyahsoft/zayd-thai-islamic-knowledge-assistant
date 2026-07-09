# TASK-08-10 — Streaming Chat API

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-CHAT-003
- FR-CHAT-004

## Objective

Expose SSE endpoints for accepted status events and final verified answer/citations.

## Scope

### In Scope

- Expose SSE endpoints for accepted status events and final verified answer/citations.
- Support cancellation, reconnect strategy and stable event schema.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-08
- TASK-08-09

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

- [x] Internal chain-of-thought is never streamed.
- [x] Citations are emitted only after verification.
- [x] Client disconnect cancels or safely detaches processing.

## Required Tests

### Unit and Contract Tests

- SSE contract tests
- Disconnect/cancellation tests
- Authorization and rate-limit tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/streaming-chat.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/chat_streaming.py` (new)
- `services/orchestrator/tests/test_chat_streaming.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_streaming_chat_api.py` (new)
- `docs/api/streaming-chat.md` (new)
- `tasks/08_orchestrator/08-10_streaming_chat_api.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/orchestrator/tests/test_chat_streaming.py services/api/tests/test_streaming_chat_api.py -q` — 9 passed
- `uv run mypy services/orchestrator/src/zayd_service_orchestrator/chat_streaming.py` — success
- `uv run ruff check --fix` and `uv run ruff format` on focused streaming files

### Acceptance Criteria Result

- SSE events expose only safe status stages and verified `final_answer` payloads; no chain-of-thought or system prompt bodies are streamed.
- `final_answer` is emitted only after orchestration completes verification, and citations are filtered to `verification_status=verified`.
- Client disconnect and explicit `DELETE /chat/streams/{stream_id}` cancel active processing and emit `cancelled` terminal events.

### Security and License Review

- Authenticated chat requires `conversations.manage_own`; guest access consumes quota before stream start.
- Per-identity stream rate limiting returns `429 CHAT_RATE_LIMITED`.
- No secrets, production data, or hidden reasoning traces were added.

### Known Limitations

- Stream reconnect history is in-memory and process-local until durable conversation streaming state is added.
- Default API composition still uses `MockLLMProvider` with an empty retriever; production wiring must supply governed retrieval and provider configuration.
- Thread CRUD endpoints from SRS §25.2 remain future chat-history tasks.

### Follow-up Tasks

- TASK-09-02 Chat Interface can consume the SSE contract documented in `docs/api/streaming-chat.md`.

### Commit

- Pending focused commit `feat(api): add streaming chat sse endpoints`