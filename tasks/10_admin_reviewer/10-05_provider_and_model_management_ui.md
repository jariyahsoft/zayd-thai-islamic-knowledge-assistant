# TASK-10-05 — Provider and Model Management UI

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-ADM-002
- FR-ADM-003

## Objective

Build provider/model configuration, primary/fallback selection, test-connection, enable/disable and safe secret update flows.

## Scope

### In Scope

- Build provider/model configuration, primary/fallback selection, test-connection, enable/disable and safe secret update flows.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-01
- TASK-03-05

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

- [ ] Secrets are write-only/masked.
- [ ] Connection tests are rate limited and audited.
- [ ] Disabling a provider shows impact and fallback readiness.

## Required Tests

### Unit and Contract Tests

- Provider configuration E2E
- Secret masking tests
- Audit tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/provider-management.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/provider_admin.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/tests/test_provider_admin.py`
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_auth_api.py`
- `services/api/tests/test_rbac_api.py`
- `apps/admin/app/admin-data.ts`
- `apps/admin/app/provider-model-ui.ts`
- `apps/admin/app/provider-model-console.tsx`
- `apps/admin/app/workspace.tsx`
- `apps/admin/app/page.tsx`
- `apps/admin/app/source-license-admin-console.tsx`
- `apps/admin/app/smoke.test.ts`
- `docs/user/provider-management.md`
- `tasks/10_admin_reviewer/10-05_provider_and_model_management_ui.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_provider_admin.py services/common/tests/test_user_admin.py services/api/tests/test_auth_api.py services/api/tests/test_rbac_api.py -q`
- `uv run ruff check services/common/src/zayd_common/provider_admin.py services/common/src/zayd_common/user_admin.py services/common/src/zayd_common/__init__.py services/common/tests/test_provider_admin.py services/common/tests/test_user_admin.py services/api/src/zayd_service_api/app.py services/api/tests/test_auth_api.py services/api/tests/test_rbac_api.py`
- `uv run mypy services/common/src/zayd_common/provider_admin.py services/common/src/zayd_common/user_admin.py services/api/src/zayd_service_api/app.py --ignore-missing-imports`
- `git diff --check`

### Acceptance Criteria Result

- [x] Secrets are write-only/masked.
- [x] Connection tests are rate limited and audited.
- [x] Disabling a provider shows impact and fallback readiness.

### Security and License Review

- Provider secret references remain write-only and are never returned in API/UI responses.
- Provider/model mutations and connection tests emit immutable audit events.
- RBAC remains server authoritative on all new provider/model routes.
- No third-party code, production secrets, or restricted religious content were added.

### Known Limitations

- Connection tests currently validate stored metadata and readiness rather than making live vendor calls.
- Frontend test/typecheck/build for `apps/admin` could not run in this environment because `node` is unavailable.
- Model routing state is stored in `configuration_json` until a dedicated schema task formalizes richer model-governance fields.

### Follow-up Tasks

- Consider a dedicated backend health adapter for real outbound provider probes once provider plugins are available.
- A future admin dashboard task can consume the new provider and model inventory data.

### Commit

- Pending
