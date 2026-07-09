# TASK-09-06 — Saved Answers

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- SRS §11 User Chat

## Objective

Allow signed-in users to save/unsave answers and display source validity status.

## Scope

### In Scope

- Allow signed-in users to save/unsave answers and display source validity status.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-09-03

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

- [x] Saved records reference answers rather than duplicate source text.
- [x] Warnings appear if citations later become invalid or suspended.

## Required Tests

### Unit and Contract Tests

- Save/unsave tests
- Invalidation display tests
- Ownership tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/saved-answers.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `database/migrations/0013_saved_answers.up.sql` (new)
- `database/migrations/0013_saved_answers.down.sql` (new)
- `database/migrations/README.md`
- `services/common/src/zayd_common/saved_answers.py` (new)
- `services/common/src/zayd_common/database/models.py`
- `services/common/tests/test_saved_answers.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_saved_answers_api.py` (new)
- `packages/saved-answers/package.json` (new)
- `packages/saved-answers/tsconfig.json` (new)
- `packages/saved-answers/src/types.ts` (new)
- `packages/saved-answers/src/api.ts` (new)
- `packages/saved-answers/src/index.ts` (new)
- `packages/saved-answers/src/saved-answers.test.ts` (new)
- `packages/citations/src/labels.ts`
- `apps/web/package.json`
- `apps/web/app/saved/page.tsx` (new)
- `apps/web/app/saved/saved-list.tsx` (new)
- `apps/web/app/saved/saved.test.ts` (new)
- `apps/web/app/chat/chat-interface.tsx`
- `apps/web/app/chat/chat-types.ts`
- `apps/web/app/page.tsx`
- `apps/web/app/globals.css`
- `docs/user/saved-answers.md` (new)
- `tasks/09_user_web/09-06_saved_answers.md`
- `tasks/00_task_index.md`
- `tasks-update.md`
- `pnpm-lock.yaml`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_saved_answers.py services/api/tests/test_saved_answers_api.py -q` — 7 passed
- `pnpm --filter @zayd/saved-answers test` — 1 passed
- `pnpm --filter @zayd/citations test` — 9 passed
- `pnpm --filter @zayd/web test` — 26 passed
- `pnpm --filter @zayd/saved-answers typecheck` — success
- `pnpm --filter @zayd/web typecheck` — success
- `pnpm --filter @zayd/web build` — success
- `uv run ruff check` on saved-answers Python files — success

### Acceptance Criteria Result

- Passed. `saved_answers` rows store only `user_id` + `answer_id`; list/detail resolve text and citations from `answers.answer_json`. UI shows `SourceStatusWarnings` for `answer_invalidated`, `citation_invalidated`, and `source_suspended` at read time.

### Security and License Review

- No secrets or production data added. Save/unsave requires auth and owned-answer checks. Audit logs omit message bodies. Rendering uses text nodes and citation cards only.

### Known Limitations

- Save controls appear only when streaming returns `answer_id` (authenticated flows with persisted answers). Guest users cannot save. Hard-delete retention policy remains operational follow-up.

### Follow-up Tasks

- TASK-09-07 — user feedback form (blocked on TASK-11-01)

### Commit

- `feat(web): add saved answers`