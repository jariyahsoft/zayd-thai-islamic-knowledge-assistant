# Multi-factor Authentication (MFA)

Privileged users — Reviewer, Senior Scholar, and Admin — must configure multi-factor authentication (MFA) before they can use protected endpoints. Zayd uses TOTP (RFC 6238) as the primary second factor and provides single-use recovery codes for fallback access.

## Scope and roles

- MFA is **enforced** for any user that holds the `reviewer`, `senior_scholar`, or `admin` role.
- Other roles may enroll MFA voluntarily but are not required to do so.
- Auditors (`auditor`), translators, data operators, and standard `user` accounts do not require MFA, although MFA enrollment is allowed.

## TOTP secrets

- Secrets are 20 random bytes per user.
- TOTP settings: SHA-1, 30-second period, 6 digits, 1-step window (RFC 6238 default).
- Secrets are stored in `auth_mfa_secrets` and only the binary secret bytes are persisted.
- `confirmed_at` is set after the user proves possession of the secret via a first successful `POST /auth/mfa/confirm`.
- Re-confirmation rotates the secret and recovery codes.

## Recovery codes

- 10 recovery codes are generated per enrollment/rotation.
- Only SHA-256 hashes of recovery codes are persisted (`auth_mfa_recovery_codes.code_hash`).
- Recovery codes have a TTL (default: 1 hour after issue) and become invalid after first use.
- Recovery code rotation is exposed via `POST /auth/mfa/recovery/rotate` for the authenticated user.

## Challenges

- A short-lived challenge is created by `POST /auth/mfa/challenge/start`.
- Each challenge is bound to a user, expires after 5 minutes, and is single-use.
- A challenge can be satisfied by a valid TOTP code (`POST /auth/mfa/challenge/verify`) or a recovery code (`POST /auth/mfa/challenge/recovery`).
- The challenge and recovery code are atomically marked as consumed when accepted.

## Reset and elevated verification

MFA reset requires one of two elevated channels:

1. `recovery_code` — the user provides an unused recovery code from their current enrollment.
2. `password_reset` — the user supplies a valid, unused `password_reset_token` issued by `POST /auth/password-reset/request`.

Both channels rotate the secret and recovery codes, and the previous recovery codes are purged. Reset actions are audited as `mfa.reset.recovery_code` or `mfa.reset.password_reset` with the user as the resource.

## Privilege enforcement

`MfaService.assert_privileged_access` is called from every privileged dependency created by `require_permission` in `services/api/src/zayd_service_api/app.py`. If the principal holds a privileged role but is not enrolled, the API returns `MFA_PRIVILEGED_ACCESS_BLOCKED` (HTTP 403). The denial is audited as `mfa.privileged_access.block` with reason `not_enrolled`.

## Errors

| Code | HTTP | Meaning |
|---|---:|---|
| `MFA_REQUIRED` | 403 | The caller must complete MFA to continue. |
| `MFA_NOT_ENROLLED` | 404 | The user has no MFA enrollment. |
| `MFA_ALREADY_ENROLLED` | 409 | The user is already enrolled. |
| `MFA_INVALID_CHALLENGE` | 404 | The challenge ID is unknown, consumed, or does not belong to the caller. |
| `MFA_INVALID_CODE` | 400 | The TOTP code is malformed or wrong. |
| `MFA_INVALID_RECOVERY_CODE` | 400 | The recovery code is unknown, used, or expired. |
| `MFA_CHALLENGE_EXPIRED` | 400 | The challenge has expired. |
| `MFA_PRIVILEGED_ACCESS_BLOCKED` | 403 | The user holds a privileged role but is not enrolled. |
| `MFA_RESET_REQUIRES_RECOVERY` | 400 | The reset proof is invalid. |
| `MFA_UNKNOWN_USER` | 404 | The user is missing, deleted, or disabled. |

## Operational notes

- Run migrations through the standard development/test runner:

  ```bash
  MIGRATION_ACTION=up make migrate
  ```

- TOTP secrets are never written to logs. Recovery code hashes are stored instead of plaintext.
- Reset proofs are validated server-side; reset operations require either a recovery code or a password reset token from the same user.
- Privileged endpoints surface the same `Authorization: Bearer …` check that the rest of the API uses, plus the `mfa.assert_privileged_access` guard.
- When a user loses access to all recovery codes, an admin with `users.manage` and active MFA must reset MFA through a future admin workflow. The current `MfaService` does not expose an admin-only reset path; this is intentionally deferred.

## Threat model

- Replay: a TOTP code is valid for ~30 seconds and only one consumption per challenge is recorded.
- Brute force: `MfaError` codes and responses do not distinguish "unknown user" from "wrong code" once enrolled; the API returns `MFA_INVALID_CODE` or `MFA_INVALID_RECOVERY_CODE` consistently.
- Auditability: every enrollment, confirmation, challenge, recovery, and reset event is recorded in `audit_logs` with `resource_type = 'mfa'`.
- Secret leaks: TOTP secrets, recovery codes, and password reset tokens are never logged.
