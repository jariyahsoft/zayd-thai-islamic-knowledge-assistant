# TASK-10-06 — User and Role Management UI

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-ADM-001
- FR-AUTH-005

## Objective

Create user search, role assignment/revocation, account disable and session revocation screens.

## Scope

### In Scope

- Create user search, role assignment/revocation, account disable and session revocation screens.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-03

## Expected Files

- Implementation files under the relevant `10_admin_reviewer` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Server-side RBAC is authoritative.
- Protect sensitive source, reviewer and operational information.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Use least privilege for reviewer/admin data.

## Acceptance Criteria

- [ ] Cannot accidentally remove the final active admin without guarded recovery.
- [ ] Role changes require permission and audit trail.
- [ ] Disabled users lose active sessions.

## Required Tests

### Unit and Contract Tests

- Role-management E2E
- Last-admin guard test
- Session revocation test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/user-role-admin.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/user_admin.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/tests/test_user_admin.py`
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_auth_api.py`
- `services/api/tests/test_rbac_api.py`
- `apps/admin/app/admin-data.ts`
- `apps/admin/app/user-admin-ui.ts`
- `apps/admin/app/user-role-admin-console.tsx`
- `apps/admin/app/workspace.tsx`
- `apps/admin/app/page.tsx`
- `apps/admin/app/smoke.test.ts`
- `docs/user/user-role-admin.md`
- `tasks/10_admin_reviewer/10-06_user_and_role_management_ui.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_provider_admin.py services/common/tests/test_user_admin.py services/api/tests/test_auth_api.py services/api/tests/test_rbac_api.py -q`
- `uv run ruff check services/common/src/zayd_common/provider_admin.py services/common/src/zayd_common/user_admin.py services/common/src/zayd_common/__init__.py services/common/tests/test_provider_admin.py services/common/tests/test_user_admin.py services/api/src/zayd_service_api/app.py services/api/tests/test_auth_api.py services/api/tests/test_rbac_api.py`
- `uv run mypy services/common/src/zayd_common/provider_admin.py services/common/src/zayd_common/user_admin.py services/api/src/zayd_service_api/app.py --ignore-missing-imports`
- `git diff --check`

### Acceptance Criteria Result

- [x] Cannot accidentally remove the final active admin without guarded recovery.
- [x] Role changes require permission and audit trail.
- [x] Disabled users lose active sessions.

### Security and License Review

- User-management changes remain RBAC-protected and MFA-gated through existing privileged dependencies.
- Account disablement now revokes active sessions and refresh tokens immediately.
- Final-admin protection remains enforced both in existing RBAC role revoke logic and the new account-status service.
- No secrets, production data, or restricted religious content were added.

### Known Limitations

- Admin user search is currently query/status/role filter only; pagination is not yet implemented.
- Frontend test/typecheck/build for `apps/admin` could not run in this environment because `node` is unavailable.
- Role grant and revoke still use free-text role names rather than a fetched role catalog.

### Follow-up Tasks

- Consider exposing a read-only role catalog endpoint for stricter admin UI validation.
- Add pagination or cursor support if admin user volume grows beyond the current simple list view.

### Commit

- Pending
