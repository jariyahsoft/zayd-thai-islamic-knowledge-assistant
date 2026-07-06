# Admin MFA Setup Guide

This guide explains how privileged users (Reviewer, Senior Scholar, and Admin) configure multi-factor authentication. MFA is required before these roles can call protected endpoints. The frontend should hide privileged navigation until `/auth/mfa/status` reports `enrolled = true`.

## Enrollment

```text
POST /auth/mfa/enroll
Authorization: Bearer <access_token>
```

Response:

```json
{
  "provisioning_uri": "otpauth://totp/Zayd:user@example.com?secret=...&issuer=Zayd",
  "secret": "<base32-encoded TOTP secret without padding>",
  "recovery_codes": [
    "abcd-1234-efgh-5678",
    "...",
    "..."
  ]
}
```

Show the `provisioning_uri` as a QR code in the admin UI or let the admin paste the `secret` into their authenticator app. The 10 recovery codes are shown **once** and should be downloaded or copied to a secure location.

```text
POST /auth/mfa/confirm
Authorization: Bearer <access_token>
Content-Type: application/json

{ "code": "123456" }
```

The 6-digit code from the authenticator must match the current TOTP window. On success, MFA is enrolled and the access token now satisfies privileged access checks.

## Privileged access

`require_permission` on protected routes automatically calls `MfaService.assert_privileged_access`. If the principal holds a privileged role and is not enrolled, the API returns `MFA_PRIVILEGED_ACCESS_BLOCKED` (HTTP 403). To resolve it, finish enrollment as above, or have an existing admin reset the role until MFA is configured.

## Status

```text
GET /auth/mfa/status
Authorization: Bearer <access_token>
```

Response:

```json
{ "enrolled": false, "privileged_role_required": true }
```

- `enrolled` — whether the user has a confirmed MFA secret.
- `privileged_role_required` — whether any of the user's roles require MFA.

## Challenge-based verification

Some sensitive operations (e.g. role grants, system administration) require a fresh challenge in addition to the access token. The frontend must:

1. Call `POST /auth/mfa/challenge/start` to receive a `challenge_id` and `expires_at`.
2. Prompt the user for either a TOTP code (then `POST /auth/mfa/challenge/verify`) or a recovery code (then `POST /auth/mfa/challenge/recovery`).
3. Retry the privileged operation once the challenge succeeds.

Both verification endpoints mark the challenge as consumed, so each `challenge_id` is single-use. Recovery code consumption also marks the code as used; the API will reject any further attempt with the same recovery code.

## Recovery code rotation

```text
POST /auth/mfa/recovery/rotate
Authorization: Bearer <access_token>
```

Response:

```json
{ "recovery_codes": ["...", "...", "..."] }
```

Rotation produces a fresh set of recovery codes and invalidates the previous set. Save the new codes immediately.

## Reset

If the admin loses access to their authenticator and recovery codes, MFA can be reset through one of two elevated channels:

```text
POST /auth/mfa/reset
Authorization: Bearer <access_token>
Content-Type: application/json

{ "channel": "recovery_code", "proof": "<an unused recovery code>" }
```

or

```text
POST /auth/mfa/reset
Authorization: Bearer <access_token>
Content-Type: application/json

{ "channel": "password_reset", "proof": "<a valid password reset token>" }
```

Reset returns a new enrollment payload (provisioning URI, secret, recovery codes) so the admin can configure a new authenticator. The previous secret and recovery codes are revoked and audited as `mfa.reset.<channel>`.

## Audit visibility

MFA enrollment, confirmation, challenge issuance, verification, recovery code use, and reset all write sanitized audit records with `resource_type = 'mfa'`. The `source_context` and `after_summary` fields include only non-sensitive metadata. Tokens, secrets, and recovery codes never appear in audit output.

## Best practices

- Store recovery codes in the same secure place used for other operational secrets.
- Use a separate authenticator app dedicated to Zayd.
- Rotate recovery codes at least every 6 months or when an admin changes devices.
- Combine MFA with the existing rate-limited login flow to protect against credential stuffing.
- Always log out from shared devices and use the per-user `revoke_all_sessions` endpoint when staff rotate.
