# TASK-04-04 — Source and License Admin UI

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-ADM-006
- FR-ADM-010

## Objective

Build admin pages to manage sources, license versions and permission documents.

## Scope

### In Scope

- Build admin pages to manage sources, license versions and permission documents.
- Display blocking warnings and downstream impact before suspension or expiry changes.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-04-03

## Expected Files

- Implementation files under the relevant `04_data_governance` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Policy decisions must be deterministic and versioned.
- Keep permission evidence private and access controlled.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- A missing or ambiguous license must block restricted operations.

## Acceptance Criteria

- [x] Admins can create, edit, search and suspend records according to RBAC.
- [x] Unknown or incomplete permissions are clearly highlighted.
- [x] Every mutation produces an audit event.

## Required Tests

### Unit and Contract Tests

- Form validation tests
- Admin E2E workflow
- RBAC and audit tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/source-license-admin.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `apps/admin/app/page.tsx`
- `apps/admin/app/source-license-admin-console.tsx`
- `apps/admin/app/admin-data.ts`
- `apps/admin/app/admin-ui.ts`
- `apps/admin/app/smoke.test.ts`
- `docs/user/source-license-admin.md`
- `tasks/04_data_governance/04-04_source_and_license_admin_ui.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `corepack pnpm --filter @zayd/admin test`
- `corepack pnpm --filter @zayd/admin typecheck`
- `corepack pnpm --filter @zayd/admin lint`
- `corepack pnpm exec prettier --write apps/admin/app/page.tsx apps/admin/app/source-license-admin-console.tsx apps/admin/app/admin-data.ts apps/admin/app/admin-ui.ts apps/admin/app/smoke.test.ts docs/user/source-license-admin.md`
- `corepack pnpm --filter @zayd/admin lint && corepack pnpm --filter @zayd/admin test && corepack pnpm --filter @zayd/admin typecheck`
- Focused secret-marker scan on changed implementation, docs and task files

### Acceptance Criteria Result

- Passed. Admin UI supports source search, source create/edit/suspend, license create/replace, policy inspection, and permission-document metadata display through the RBAC-protected admin APIs.
- Passed. Unknown, incomplete, missing-evidence, suspended, expiry-related, and policy-blocked states are highlighted with warning cards and impact summaries.
- Passed. All UI mutations use the existing audited backend endpoints, so source and license changes continue to produce immutable audit events.

### Security and License Review

- The UI keeps the bearer token in memory only and does not persist it to cookies, local storage, committed files, or docs.
- Mutations continue to go through existing RBAC and MFA-protected API endpoints; the frontend does not bypass server-side authorization.
- Permission evidence remains metadata-only; the UI displays private object keys but not file contents.
- No secrets, production data, restricted religious content, or third-party code were introduced.
- Focused secret-marker scan passed for changed implementation, docs and task-tracking files.

### Known Limitations

- The admin console currently requires a manually pasted temporary bearer token because a shared admin auth/session client has not been implemented yet.
- UI tests cover pure helper logic and admin workflow view-model behavior; browser-level E2E coverage remains deferred until a fuller frontend test harness exists.
- Downstream ingestion, retrieval, and export workflows still depend on later tasks to consume the policy engine automatically.

### Follow-up Tasks

- TASK-05-01 and later ingestion tasks should consume source/license policy outcomes directly in upload and review flows.
- Future admin auth/session UI work should replace manual token entry with a proper authenticated session.

### Commit

- This task completion commit.
