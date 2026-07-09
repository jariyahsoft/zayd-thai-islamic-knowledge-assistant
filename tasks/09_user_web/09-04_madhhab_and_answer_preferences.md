# TASK-09-04 — Madhhab and Answer Preferences

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- FR-MADH-001
- FR-CHAT-005

## Objective

Implement settings for madhhab, answer length, Arabic visibility, history mode and theme.

## Scope

### In Scope

- Implement settings for madhhab, answer length, Arabic visibility, history mode and theme.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

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

- [x] Default Shafii setting is disclosed, not hidden.
- [x] Preferences are validated and synced for signed-in users.
- [x] Guest preferences remain local and privacy-safe.

## Required Tests

### Unit and Contract Tests

- Preference persistence tests
- Default disclosure test
- Validation tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/preferences.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `database/migrations/0012_user_app_preferences.up.sql` (new)
- `database/migrations/0012_user_app_preferences.down.sql` (new)
- `database/migrations/README.md`
- `services/common/src/zayd_common/database/models.py`
- `services/common/src/zayd_common/user_preferences.py` (new)
- `services/common/tests/test_user_preferences.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_preferences_api.py` (new)
- `packages/preferences/package.json` (new)
- `packages/preferences/tsconfig.json` (new)
- `packages/preferences/src/types.ts` (new)
- `packages/preferences/src/defaults.ts` (new)
- `packages/preferences/src/labels.ts` (new)
- `packages/preferences/src/validation.ts` (new)
- `packages/preferences/src/storage.ts` (new)
- `packages/preferences/src/api.ts` (new)
- `packages/preferences/src/index.ts` (new)
- `packages/preferences/src/preferences.test.ts` (new)
- `apps/web/package.json`
- `apps/web/app/preferences/preferences-provider.tsx` (new)
- `apps/web/app/preferences/use-user-preferences.ts` (new)
- `apps/web/app/settings/settings-form.tsx` (new)
- `apps/web/app/settings/settings.test.ts` (new)
- `apps/web/app/settings/page.tsx`
- `apps/web/app/user-app-client.tsx`
- `apps/web/app/chat/chat-interface.tsx`
- `apps/web/app/chat/chat-stream.ts`
- `apps/web/app/chat/page.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/history/page.tsx`
- `apps/web/app/citations/[citationId]/page.tsx`
- `apps/web/app/globals.css`
- `docs/user/preferences.md` (new)
- `tasks/09_user_web/09-04_madhhab_and_answer_preferences.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_user_preferences.py services/api/tests/test_preferences_api.py -q` — 7 passed
- `pnpm --filter @zayd/preferences test` — 6 passed
- `pnpm --filter @zayd/web test` — 22 passed
- `pnpm --filter @zayd/preferences typecheck` — success
- `pnpm --filter @zayd/web typecheck` — success
- `pnpm --filter @zayd/web build` — success
- `uv run ruff check` on preference Python files — success after line-length/import fixes

### Acceptance Criteria Result

- Passed. Settings UI discloses default Shafii madhhab in Thai and via API `default_madhhab`. Signed-in users sync madhhab, answer length, Arabic visibility, and history mode through `/auth/me/preferences` with validation and audit logging. Guests persist all preferences locally in `zayd.preferences.guest` without server calls. Theme stays client-only.

### Security and License Review

- No secrets or production data added. Guest preferences never sync until sign-in. Preference mutations require bearer auth and write hash-chained audit summaries only. Invalid API payloads fail closed with structured errors.

### Known Limitations

- Theme is not stored server-side by design. Madhhab default disclosure text requires human religious-content review before production. Migration `0012` needs DBA review before production rollout.

### Follow-up Tasks

- TASK-09-05 — conversation history screen (already READY)

### Commit

- `feat(web): add madhhab and answer preferences`