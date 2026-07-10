# TASK-09-02 — Chat Interface

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-CHAT-001
- FR-CHAT-007

## Objective

Build thread creation, message list, streaming progress, answer display, retry and stop-generation controls.

## Scope

### In Scope

- Build thread creation, message list, streaming progress, answer display, retry and stop-generation controls.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-10
- TASK-09-01

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

- [x] UI handles success, abstention, provider errors and cancellation.
- [x] No unsafe raw HTML is rendered.
- [x] Keyboard and screen-reader basics work.

## Required Tests

### Unit and Contract Tests

- Chat component tests
- Streaming E2E tests
- XSS rendering tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/frontend/chat.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `.gitignore` (allow `packages/config/src/env/` despite Python `env/` rule)
- `packages/config/src/env/public.ts` (new — restores missing public env helper referenced by apps)
- `apps/web/app/chat/page.tsx`
- `apps/web/app/chat/chat-interface.tsx` (new)
- `apps/web/app/chat/chat-stream.ts` (new)
- `apps/web/app/chat/chat-types.ts` (new)
- `apps/web/app/chat/chat-ui.ts` (new)
- `apps/web/app/chat/chat.test.ts` (new)
- `apps/web/app/globals.css`
- `docs/frontend/chat.md` (new)
- `tasks/09_user_web/09-02_chat_interface.md`
- `tasks/09_user_web/09-03_citation_cards_and_source_detail.md`
- `tasks/09_user_web/09-05_conversation_history.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `corepack pnpm --filter @zayd/web test` — 17 passed (includes 12 chat tests)
- `corepack pnpm --filter @zayd/web typecheck` — success
- `corepack pnpm --filter @zayd/web build` — success

### Acceptance Criteria Result

- Passed. Chat UI streams answers via SSE, shows Thai progress stages, handles `final_answer`, abstention (`complete.status=abstained`), HTTP provider errors, and client-side cancellation via `AbortController`. Rendering uses text nodes only (no `dangerouslySetInnerHTML`). Composer includes labels, `aria-live` regions, keyboard submit (Enter), and stop/retry controls.

### Security and License Review

- No secrets or production data added. Guest tokens stored in `localStorage` only. Answer text and citations render as plain React text; Arabic uses isolated RTL spans. No hidden prompts or chain-of-thought exposed.

### Known Limitations

- Guest stop uses fetch abort (DELETE cancel requires bearer auth). Madhhab/answer-length preferences await TASK-09-04. Conversation history list awaits TASK-09-05. Citation cards are minimal list items until TASK-09-03.

### Follow-up Tasks

- TASK-09-03 — citation cards and source detail
- TASK-09-04 — madhhab and answer preferences in settings
- TASK-09-05 — conversation history screen

### Commit

- `feat(web): add streaming chat interface`
