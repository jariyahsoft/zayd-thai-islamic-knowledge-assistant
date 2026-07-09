# TASK-09-05 — Conversation History

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-CHAT-009
- FR-CHAT-011

## Objective

Implement list, search, open, delete, delete-all and no-history mode.

## Scope

### In Scope

- Implement list, search, open, delete, delete-all and no-history mode.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-01
- TASK-09-02

## Expected Files

- Implementation files under the relevant `09_user_web` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use generated API clients/contracts where available.
- Meet responsive, accessibility and safe-rendering requirements.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Sanitize rendered content and avoid leaking internal traces.

## Acceptance Criteria

- [x] Users access only their own threads.
- [x] Deletion/retention behavior follows policy.
- [x] No-history mode avoids persistent message storage except required abuse/security metadata.

## Required Tests

### Unit and Contract Tests

- Ownership authorization tests
- Deletion E2E tests
- No-history persistence tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/conversation-history.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/conversations.py` (new)
- `services/common/src/zayd_common/database/models.py`
- `services/common/tests/test_conversations.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_conversation_history_api.py` (new)
- `services/orchestrator/src/zayd_service_orchestrator/chat_streaming.py`
- `services/orchestrator/tests/test_chat_streaming.py`
- `packages/conversations/package.json` (new)
- `packages/conversations/tsconfig.json` (new)
- `packages/conversations/src/types.ts` (new)
- `packages/conversations/src/api.ts` (new)
- `packages/conversations/src/index.ts` (new)
- `packages/conversations/src/conversations.test.ts` (new)
- `apps/web/package.json`
- `apps/web/app/history/page.tsx`
- `apps/web/app/history/history-list.tsx` (new)
- `apps/web/app/history/history.test.ts` (new)
- `apps/web/app/chat/page.tsx`
- `apps/web/app/chat/chat-interface.tsx`
- `apps/web/app/globals.css`
- `docs/user/conversation-history.md` (new)
- `tasks/09_user_web/09-05_conversation_history.md`
- `tasks/00_task_index.md`
- `tasks-update.md`
- `pnpm-lock.yaml`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_conversations.py services/api/tests/test_conversation_history_api.py services/orchestrator/tests/test_chat_streaming.py -q` — 14 passed
- `pnpm --filter @zayd/conversations test` — 1 passed
- `pnpm --filter @zayd/web test` — 24 passed
- `pnpm --filter @zayd/conversations typecheck` — success
- `pnpm --filter @zayd/web typecheck` — success
- `pnpm --filter @zayd/web build` — success
- `uv run ruff check` on conversation Python files — success

### Acceptance Criteria Result

- Passed. History APIs enforce `conversations.manage_own` and ownership checks with 404 for foreign threads. Soft-delete plus audit logging follow repository retention patterns. No-history mode redacts persisted bodies, excludes threads from history APIs, and keeps hashes/metadata for security review.

### Security and License Review

- No secrets or production data added. Delete mutations audit without message bodies. History UI uses text-only rendering. Guests are blocked from server history with clear local/no-history messaging.

### Known Limitations

- Guest server-side history remains out of scope. Conversation search is title/first-question only. Hard-delete/TTL retention policy is operational follow-up outside this task.

### Follow-up Tasks

- TASK-09-06 — saved answers (already READY)

### Commit

- `feat(web): add conversation history`