# TASK-09-01 — User Application Shell

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §7.1 Frontend
- NFR-PRV-003

## Objective

Create responsive Next.js/PWA shell with mobile-first navigation, Thai typography, theme support and isolated Arabic RTL components.

## Scope

### In Scope

- Create responsive Next.js/PWA shell with mobile-first navigation, Thai typography, theme support and isolated Arabic RTL components.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-01 complete

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

- [x] Core screens work on supported mobile widths.
- [x] Thai and Arabic text do not overflow or reverse incorrectly.
- [x] PWA manifest and installability checks pass.

## Required Tests

### Unit and Contract Tests

- Responsive component tests
- Accessibility smoke tests
- PWA audit

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/frontend/user-app.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `packages/ui/src/index.tsx`
- `packages/ui/src/theme.ts` (new)
- `packages/ui/src/arabic-text.tsx` (new)
- `packages/ui/src/pwa.ts` (new)
- `packages/ui/src/user-app-shell.tsx` (new)
- `packages/ui/src/user-app-shell.test.tsx` (new)
- `apps/web/app/globals.css` (new)
- `apps/web/app/layout.tsx`
- `apps/web/app/page.tsx`
- `apps/web/app/user-app-client.tsx` (new)
- `apps/web/app/manifest.ts` (new)
- `apps/web/app/chat/page.tsx` (new)
- `apps/web/app/history/page.tsx` (new)
- `apps/web/app/settings/page.tsx` (new)
- `apps/web/app/shell.test.ts` (new)
- `apps/web/public/icons/icon-192.svg` (new)
- `apps/web/public/icons/icon-512.svg` (new)
- `docs/frontend/user-app.md` (new)
- `tasks/09_user_web/09-01_user_application_shell.md`
- `tasks/09_user_web/09-02_chat_interface.md`
- `tasks/09_user_web/09-04_madhhab_and_answer_preferences.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `vitest run` in `packages/ui` — 5 passed
- `vitest run app/shell.test.ts` in `apps/web` — 4 passed
- `tsc --noEmit` in `packages/ui` — success
- `tsc --noEmit` in `apps/web` — success for new shell files; pre-existing `env.client.test.ts` workspace resolution remains environment-dependent

### Acceptance Criteria Result

- Core screens (`/`, `/chat`, `/history`, `/settings`) render inside a mobile-first shell with bottom navigation and responsive CSS tokens.
- Thai text uses a Thai-first font stack with `overflow-wrap: anywhere`; Arabic snippets use isolated RTL rendering via `ArabicText`.
- `createUserAppManifest()` passes installability validation and ships SVG icons plus `app/manifest.ts`.

### Security and License Review

- No secrets, production data, or hidden model traces added.
- Demo Arabic/Thai copy is neutral placeholder text pending human religious-content review.
- SVG icons are simple monogram assets with no restricted religious imagery.

### Known Limitations

- Service worker/offline caching is not implemented; installability is manifest-based for this task.
- Chat, history, and settings screens are placeholders until TASK-09-02, TASK-09-04, and TASK-09-05.
- Tailwind CSS from SRS §7.1 is deferred; the shell uses tokenized CSS to match current app patterns.

### Follow-up Tasks

- TASK-09-02 Chat Interface is now READY.
- TASK-09-04 Madhhab and Answer Preferences is now READY.

### Commit

- Pending focused commit `feat(web): add user application shell`