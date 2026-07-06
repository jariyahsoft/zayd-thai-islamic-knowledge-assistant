# TASK-03-04 — Implement MFA for Privileged Users

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-AUTH-004
- NFR-SEC-004

## Objective

Add TOTP-based MFA for reviewer, senior scholar and admin roles.

## Scope

### In Scope

- Add TOTP-based MFA for reviewer, senior scholar and admin roles.
- Provide single-use recovery codes and secure reset workflow.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-03

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

- [x] Privileged access is blocked until MFA is configured and verified.
- [x] Recovery codes are hashed, single-use and rotatable.
- [x] MFA reset is audited and requires elevated verification.

## Required Tests

### Unit and Contract Tests

- TOTP verification tests
- Recovery-code reuse test
- Privileged-login E2E tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/security/mfa.md`
- `docs/user/admin-mfa.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/mfa.py` — TOTP-based MFA service with enrollment, confirmation, challenge, recovery, reset, and privileged-access assertion
- `services/common/src/zayd_common/database/models.py` — `AuthMfaSecret`, `AuthMfaRecoveryCode`, and `AuthMfaChallenge` ORM models
- `services/common/src/zayd_common/__init__.py` — MFA service and type exports
- `services/api/src/zayd_service_api/app.py` — MFA request/response models, `mfa_service` dependency, MFA dependency that enforces privileged access, MFA error handler, and `/auth/mfa/*` routes
- `database/migrations/0005_mfa_privileged.up.sql` — MFA tables, indexes, and trigger
- `database/migrations/0005_mfa_privileged.down.sql` — development/test rollback
- `database/migrations/README.md` — migration registry update
- `services/common/tests/test_mfa.py` — TOTP, enrollment, recovery, privileged-access, and reset tests
- `services/api/tests/test_mfa_api.py` — endpoint success and failure tests
- `services/api/tests/test_rbac_api.py` — RBAC test updated to enroll admin MFA before exercising privileged endpoint
- `docs/security/mfa.md` — MFA security model and operational notes
- `docs/user/admin-mfa.md` — admin MFA setup guide
- `tasks/03_auth/03-04_implement_mfa_for_privileged_users.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

```bash
uv run pytest services/common/tests/test_mfa.py services/api/tests/test_mfa_api.py
uv run pytest services/api/tests/test_rbac_api.py services/api/tests/test_mfa_api.py services/common/tests/test_mfa.py services/common/tests/test_rbac.py
uv run ruff check services/common/src/zayd_common/mfa.py services/common/src/zayd_common/__init__.py services/common/src/zayd_common/database/models.py services/api/src/zayd_service_api/app.py services/common/tests/test_mfa.py services/api/tests/test_mfa_api.py services/api/tests/test_rbac_api.py
uv run ruff format --check services/common/src/zayd_common/mfa.py services/common/src/zayd_common/__init__.py services/common/src/zayd_common/database/models.py services/api/src/zayd_service_api/app.py services/common/tests/test_mfa.py services/api/tests/test_mfa_api.py services/api/tests/test_rbac_api.py
uv run mypy services/common/src/zayd_common/mfa.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py
uv run pytest
MIGRATION_ACTION=up make migrate
uv run python - <<'PY'
from pathlib import Path
for path in [
    Path('services/common/src/zayd_common/mfa.py'),
    Path('services/common/src/zayd_common/__init__.py'),
    Path('services/common/src/zayd_common/database/models.py'),
    Path('services/api/src/zayd_service_api/app.py'),
    Path('services/common/tests/test_mfa.py'),
    Path('services/api/tests/test_mfa_api.py'),
    Path('services/api/tests/test_rbac_api.py'),
    Path('database/migrations/0005_mfa_privileged.up.sql'),
    Path('database/migrations/0005_mfa_privileged.down.sql'),
    Path('database/migrations/README.md'),
    Path('docs/security/mfa.md'),
    Path('docs/user/admin-mfa.md'),
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

- [x] Privileged access is blocked until MFA is configured and verified: `MfaService.assert_privileged_access` is invoked from every `require_permission` dependency and returns `MFA_PRIVILEGED_ACCESS_BLOCKED` until the principal is enrolled.
- [x] Recovery codes are hashed, single-use and rotatable: `AuthMfaRecoveryCode.code_hash` is a SHA-256 digest, `used_at` enforces single-use, and `rotate_recovery_codes` issues a fresh set.
- [x] MFA reset is audited and requires elevated verification: `MfaService.reset_mfa` requires a recovery code or password reset token and writes `mfa.reset.<channel>` audit entries with the actor and trace id.

### Security and License Review

- TOTP implementation follows RFC 6238 with SHA-1, 30-second period, 6 digits, 1-step window, and 20-byte secrets generated from `secrets.token_bytes`.
- TOTP secrets and password reset tokens are never logged. Recovery codes are persisted as SHA-256 hashes only.
- Privileged-access denials, enrollment failures, challenge failures, and reset actions are audited with sanitized metadata.
- `MfaError` and `RbacError` use stable non-enumerating error codes; for example, an invalid TOTP code returns `MFA_INVALID_CODE` regardless of whether the secret exists.
- No third-party code, production secrets, production data, or restricted religious content were introduced.

### Known Limitations

- Admin-only MFA reset (where the actor is a different admin) is intentionally out of scope; a follow-up task must add a privileged reset endpoint that is itself protected by MFA.
- Email delivery for MFA recovery codes or challenges is not implemented; trusted users receive codes out-of-band.
- Recovery code TTL is enforced server-side; future work may move TTL to a per-tenant policy.

### Follow-up Tasks

- TASK-03-05 - Implement Immutable Audit Log
- Future admin-only MFA reset workflow
- Future UX flows for QR enrollment and recovery code backup

### Commit

- Not created in this run because the active runtime policy requires an explicit user request before committing.
