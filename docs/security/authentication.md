# Authentication Security

Zayd uses server-side authentication records and opaque refresh tokens.

## Passwords

- Passwords are stored with PBKDF2-HMAC-SHA256, a per-password random salt, and 310,000 iterations.
- Plaintext passwords are accepted only at registration, login, and reset boundaries.
- Passwords and tokens are not written to audit records, logs, or API error responses.

## Sessions And Tokens

- Access tokens are short-lived HS256 signed bearer tokens.
- Refresh tokens are opaque random strings and only SHA-256 hashes are stored.
- Refresh tokens rotate on every refresh.
- Reuse of an already-used refresh token revokes the related session and all refresh tokens for that session.
- Users can revoke all active sessions.

## Rate Limits

- Login and password reset requests are rate limited by hashed action bucket.
- Rate-limit records store hashed bucket identifiers instead of plaintext credentials or tokens.

## Audit Events

Authentication events are written to `audit_logs` with action, outcome, actor where available, resource, reason, trace id, and sanitized summaries.
