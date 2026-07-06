# TASK-03-01 — Implement User Authentication

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-AUTH-001
- FR-AUTH-005
- NFR-SEC-002

## Objective

Implement registration, login, refresh-token rotation, logout, password reset and session revocation.

## Scope

### In Scope

- Implement registration, login, refresh-token rotation, logout, password reset and session revocation.
- Use secure password hashing and server-side session/token records.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-02 complete

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

- [ ] Passwords use an approved adaptive hash.
- [ ] Refresh-token reuse is detected and related sessions are revoked.
- [ ] Login and reset endpoints are rate limited.
- [ ] Users can revoke all active sessions.
- [ ] Authentication events are auditable without logging secrets.

## Required Tests

### Unit and Contract Tests

- Authentication unit tests
- Token rotation and reuse tests
- Rate-limit integration tests
- Session revocation E2E test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/security/authentication.md`
- `docs/api/authentication.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/auth.py`
- `services/common/src/zayd_common/database/models.py`
- `services/common/src/zayd_common/__init__.py`
- `services/api/src/zayd_service_api/app.py`
- `database/migrations/0002_auth_token_rotation.up.sql`
- `database/migrations/0002_auth_token_rotation.down.sql`
- `scripts/migrate.sh`
- `database/migrations/README.md`
- `services/common/tests/test_auth.py`
- `services/api/tests/test_auth_api.py`
- `docs/security/authentication.md`
- `docs/api/authentication.md`
- `tasks/03_auth/03-01_implement_user_authentication.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_auth.py services/api/tests/test_auth_api.py`
- `uv run pytest services/common/tests/test_auth.py services/api/tests/test_auth_api.py services/common/tests/test_database.py services/common/tests/test_seeding.py`
- `uv run pytest database/tests/test_initial_migration.py`
- `MIGRATION_ACTION=up make migrate`
- `uv run ruff check services/common/src/zayd_common/auth.py services/api/src/zayd_service_api/app.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/common/tests/test_auth.py services/api/tests/test_auth_api.py`
- `uv run ruff format --check services/common/src/zayd_common/auth.py services/api/src/zayd_service_api/app.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/common/tests/test_auth.py services/api/tests/test_auth_api.py`
- `uv run mypy services/common/src/zayd_common/auth.py services/api/src/zayd_service_api/app.py`
- `bash -n scripts/migrate.sh`

### Acceptance Criteria Result

- [x] Passwords use an approved adaptive hash.
- [x] Refresh-token reuse is detected and related sessions are revoked.
- [x] Login and reset endpoints are rate limited.
- [x] Users can revoke all active sessions.
- [x] Authentication events are auditable without logging secrets.

### Security and License Review

- Passwords use PBKDF2-HMAC-SHA256 with per-password salts and 310,000 iterations.
- Refresh tokens and reset tokens are opaque random values; only SHA-256 hashes are stored.
- Access tokens are short-lived signed bearer tokens.
- Login, reset, refresh, logout and session-revocation events write sanitized audit log records.
- Tests verify audit records do not contain plaintext passwords.
- No secrets, production data, restricted religious content, or new third-party code were introduced.

### Known Limitations

- Email delivery for password reset is not implemented yet; the development API returns the reset token for local/test workflows.
- MFA and RBAC authorization policy are deferred to follow-up tasks.
- The current access-token implementation is intentionally minimal HS256 signing without a JWKS/key-rotation layer.

### Follow-up Tasks

- TASK-03-02 - Implement Guest Sessions
- TASK-03-03 - Implement RBAC
- TASK-03-04 - Implement MFA for Privileged Users
- TASK-03-05 - Implement Immutable Audit Log

### Commit

- Pending
