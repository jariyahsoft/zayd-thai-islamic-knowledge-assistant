# TASK-03-03 — Implement RBAC

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §10 Users and Roles
- FR-AUTH-007
- NFR-SEC-006

## Objective

Implement roles, permissions and authorization dependencies/middleware.

## Scope

### In Scope

- Implement roles, permissions and authorization dependencies/middleware.
- Cover document, answer, provider, license, user and audit capabilities.
- Enforce separation-of-duties rules.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-01

## Expected Files

- Implementation files under the relevant `03_auth` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use server-side enforcement and least privilege.
- Do not log credentials, tokens or sensitive recovery material.
- Return stable, non-enumerating error responses.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Apply OWASP authentication/session guidance and rate limiting.

## Acceptance Criteria

- [x] Every protected endpoint enforces permissions server-side.
- [x] Uploading users cannot approve their own restricted work.
- [x] Authorization failures return consistent non-leaking errors.
- [x] Permission changes are audited.

## Required Tests

### Unit and Contract Tests

- Permission matrix tests
- Horizontal and vertical privilege-escalation tests
- Endpoint authorization integration tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/security/rbac.md`
- `docs/api/authorization.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/rbac.py` — canonical permissions, role matrix, RBAC service, bootstrap, role grants/revocations, permission checks, self-approval guard, and last-admin safeguard
- `services/common/src/zayd_common/auth.py` — default registered-user role assignment during registration
- `services/common/src/zayd_common/database/models.py` — ORM models for permissions and role-permission assignments
- `services/common/src/zayd_common/database/__init__.py` — RBAC model exports
- `services/common/src/zayd_common/__init__.py` — RBAC service and type exports
- `services/api/src/zayd_service_api/app.py` — bearer principal dependency, permission dependency, `/auth/me`, role admin endpoints, RBAC bootstrap endpoint, and document-approval authorization check endpoint
- `database/migrations/0004_rbac_seed.up.sql` — system permissions, roles, and permission matrix seed
- `database/migrations/0004_rbac_seed.down.sql` — development/test rollback for RBAC seed data
- `database/migrations/README.md` — migration registry update
- `services/common/tests/test_rbac.py` — permission-matrix, privilege-escalation, audit, separation-of-duties, and last-admin tests
- `services/api/tests/test_rbac_api.py` — endpoint authorization success/failure tests
- `services/api/tests/test_auth_api.py` — OpenAPI/route coverage for RBAC endpoints
- `docs/security/rbac.md` — RBAC security model and operational notes
- `docs/api/authorization.md` — authorization API behavior and stable errors
- `tasks/03_auth/03-03_implement_rbac.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

```bash
uv run pytest services/common/tests/test_rbac.py services/api/tests/test_rbac_api.py services/api/tests/test_auth_api.py
uv run ruff check services/common/src/zayd_common/rbac.py services/common/src/zayd_common/auth.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/database/__init__.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_rbac.py services/api/tests/test_rbac_api.py services/api/tests/test_auth_api.py
uv run ruff format --check services/common/src/zayd_common/rbac.py services/common/src/zayd_common/auth.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/database/__init__.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_rbac.py services/api/tests/test_rbac_api.py services/api/tests/test_auth_api.py
uv run mypy services/common/src/zayd_common/rbac.py services/common/src/zayd_common/auth.py services/common/src/zayd_common/database/models.py services/api/src/zayd_service_api/app.py
uv run pytest services/common/tests/test_rbac.py services/api/tests/test_rbac_api.py services/api/tests/test_auth_api.py services/common/tests/test_auth.py services/common/tests/test_guest.py services/api/tests/test_guest_api.py
uv run pytest
MIGRATION_ACTION=up make migrate
uv run python - <<'PY'
from pathlib import Path
for path in [
    Path('services/common/src/zayd_common/rbac.py'),
    Path('services/common/src/zayd_common/auth.py'),
    Path('services/common/src/zayd_common/database/models.py'),
    Path('services/api/src/zayd_service_api/app.py'),
    Path('services/common/tests/test_rbac.py'),
    Path('services/api/tests/test_rbac_api.py'),
    Path('database/migrations/0004_rbac_seed.up.sql'),
    Path('database/migrations/0004_rbac_seed.down.sql'),
    Path('docs/security/rbac.md'),
    Path('docs/api/authorization.md'),
]:
    text = path.read_text()
    forbidden = ['8733454851', '8884817724', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    hits = [marker for marker in forbidden if marker in text]
    if hits:
        raise SystemExit(f'secret marker found in {path}: {hits}')
print('secret marker scan passed')
PY
```

### Acceptance Criteria Result

- [x] Every protected endpoint enforces permissions server-side: `/auth/sessions/revoke-all`, `/auth/me`, `/admin/rbac/bootstrap`, `/admin/users/roles/grant`, `/admin/users/roles/revoke`, and `/authorization/documents/approve` all require bearer auth and/or RBAC checks.
- [x] Uploading users cannot approve their own restricted work: `RbacService.assert_can_approve_document` returns `RBAC_SEPARATION_OF_DUTIES` when actor and uploader match.
- [x] Authorization failures return consistent non-leaking errors: `AuthError` and `RbacError` use stable `{error: {code, message}}` envelopes.
- [x] Permission changes are audited: role grant/revoke actions and denied permission checks create sanitized `audit_logs` entries.

### Security and License Review

- RBAC checks are server-side and fail closed for unknown permissions, unknown roles, inactive users, and missing bearer tokens.
- New accounts receive only the least-privilege `user` role.
- Guests have no privileged permissions and cannot satisfy bearer-protected dependencies.
- Auditors are read-only and cannot mutate roles, providers, licenses, documents, prompts, models, or users.
- The final active admin role assignment cannot be revoked.
- Audit entries use compact metadata and do not include credentials, tokens, full request bodies, production payloads, or restricted religious content.
- No third-party code, production secrets, production data, or restricted religious content were introduced.

### Known Limitations

- The RBAC bootstrap endpoint requires an already-authorized role manager; initial admin provisioning remains delegated to the existing trusted seed/admin workflow.
- Later domain endpoints must adopt `require_permission` or `RbacService` as they are implemented in future epics.
- MFA for privileged users remains deferred to TASK-03-04.
- Immutable audit hardening remains deferred to TASK-03-05.

### Follow-up Tasks

- TASK-03-04 - Implement MFA for Privileged Users
- TASK-03-05 - Implement Immutable Audit Log
- Future domain API tasks must apply the documented permission dependencies to their new endpoints.

### Commit

- Not created in this run because the active runtime policy requires an explicit user request before committing.
