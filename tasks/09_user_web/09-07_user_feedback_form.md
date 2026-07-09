# TASK-09-07 — User Feedback Form

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- FR-FDB-001
- FR-FDB-004

## Objective

Create an accessible feedback form with categorized issue types and optional notes linked to the answer.

## Scope

### In Scope

- Create an accessible feedback form with categorized issue types and optional notes linked to the answer.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-11-01

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

- [x] Internal traces are not exposed.
- [x] Submission is rate limited and confirms receipt.
- [x] Sensitive free text is handled under retention/privacy policy.

## Required Tests

### Unit and Contract Tests

- Form validation tests
- Feedback submission E2E
- Rate-limit test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/report-answer.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/feedback.py` (new)
- `services/common/tests/test_feedback.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_feedback_api.py` (new)
- `packages/feedback/package.json` (new)
- `packages/feedback/tsconfig.json` (new)
- `packages/feedback/src/types.ts` (new)
- `packages/feedback/src/labels.ts` (new)
- `packages/feedback/src/validation.ts` (new)
- `packages/feedback/src/api.ts` (new)
- `packages/feedback/src/index.ts` (new)
- `packages/feedback/src/feedback.test.ts` (new)
- `apps/web/package.json`
- `apps/web/app/chat/chat-interface.tsx`
- `apps/web/app/chat/chat.test.ts`
- `apps/web/app/globals.css`
- `docs/user/report-answer.md` (new)
- `docs/api/feedback.md` (new)
- `tasks/09_user_web/09-07_user_feedback_form.md`
- `tasks/11_feedback/11-01_feedback_api.md`
- `tasks/00_task_index.md`
- `tasks-update.md`
- `pnpm-lock.yaml`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_feedback.py services/api/tests/test_feedback_api.py -q` — 7 passed
- `uv run ruff check` on feedback Python files — success
- `pnpm --filter @zayd/feedback test` — 5 passed
- `pnpm --filter @zayd/feedback typecheck` — success
- `pnpm --filter @zayd/web test` — 27 passed
- `pnpm --filter @zayd/web typecheck` — success
- `pnpm --filter @zayd/web build` — success

### Acceptance Criteria Result

- Passed. Public API/UI responses expose only receipt fields. Rate limit enforced at 10/hour/user. Audit logs store `notes_length` without note body; optional notes stored in `feedback.body` under existing retention policy.

### Security and License Review

- No secrets or production data added. Submit/read requires `feedback.create` and owned-answer checks. Form uses text nodes only (no `dangerouslySetInnerHTML`). Internal trace/version metadata stays in audit logs only.

### Known Limitations

- Report controls require signed-in users with persisted `answer_id`. Rate limiter is in-memory per API process. Reviewer queue UI remains TASK-11-02.

### Follow-up Tasks

- TASK-11-02 — feedback review queue

### Commit

- `feat(web): add user feedback form`
