# Guest Sessions

## Overview

Zayd exposes an anonymous guest session flow so first-time visitors can ask one or two questions before registering. Guest sessions:

- never carry user identity
- expire automatically after a configured TTL
- carry a per-session message quota to limit abuse
- upgrade cleanly into a full registered user without leaking data

This document describes the data model, the public surface area, and the privilege boundary.

## Data Model

A guest session is stored in the `guest_sessions` table:

| Column | Description |
|---|---|
| `id` | UUID primary key |
| `session_token_hash` | SHA-256 hash of the opaque bearer token (token is never persisted) |
| `ip_hash` | SHA-256 hash of the originating IP (optional) |
| `user_agent_hash` | SHA-256 hash of the User-Agent (optional) |
| `converted_user_id` | Set on successful conversion; FK to `auth_users.id` |
| `message_quota` | Maximum number of chat turns allowed |
| `messages_used` | Number of turns already consumed |
| `expires_at` | Hard TTL for the session |
| `last_seen_at` | Last successful `validate_session` call (when `touch=True`) |
| `revoked_at` | Set on logout, conversion, or admin action |
| `created_at` / `updated_at` | Standard audit timestamps |

The migration is `database/migrations/0003_guest_sessions.up.sql` (down at `0003_guest_sessions.down.sql`).

## Settings

| Env var | Default | Description |
|---|---|---|
| `ENABLE_GUEST_MODE` | `true` | Master switch for guest endpoints |
| `GUEST_SESSION_TTL_MINUTES` | `120` | TTL of a freshly issued session |
| `GUEST_MESSAGE_QUOTA` | `10` | Default message quota per session |

## Service Surface

The `GuestService` (`services/common/src/zayd_common/guest.py`) exposes:

- `start_session` — mints a new token, persists the hash, and returns a `GuestSessionInfo` snapshot
- `validate_session` — verifies TTL, revocation, and quota state (also bumps `last_seen_at` when `touch=True`)
- `consume_quota` — counts one message against the session, raising `GUEST_QUOTA_EXCEEDED` past the limit
- `revoke_session` — soft-revokes the session (logout or admin action)
- `convert_to_user` — calls `AuthService.register`, links `converted_user_id`, and revokes the guest

All audit events are written to `audit_logs` with `resource_type="guest_session"`. Stable error codes:

| Code | Meaning | HTTP |
|---|---|---|
| `GUEST_DISABLED` | Guest mode is administratively disabled | 403 |
| `GUEST_INVALID_SESSION` | Token not recognised or revoked | 401 |
| `GUEST_REVOKED` | Session is revoked (logout/converted) | 401 |
| `GUEST_EXPIRED` | TTL elapsed | 401 |
| `GUEST_QUOTA_EXCEEDED` | Quota exhausted | 429 |
| `GUEST_ALREADY_CONVERTED` | Conversion attempted on a converted session | 409 |

## API Surface

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/guest/start` | Public | Mint a new guest session |
| `POST` | `/auth/guest/convert` | Public + guest token | Convert to a registered user |

Authenticated user routes remain protected by the standard `Bearer` access token. Guests cannot access any privileged route and cannot reuse converted or revoked tokens.

## Conversion Semantics

`convert_to_user` registers a new user, links the guest row to the new `auth_users.id`, and revokes the guest session in a single transaction. Only the explicit registration payload (email, display name, initial password) is preserved; chat history and other data flows through follow-up tasks and are out of scope for the guest boundary.

## Security Notes

- Tokens are 32 bytes of `secrets.token_urlsafe` randomness; only the SHA-256 hash is persisted.
- IP and User-Agent are hashed before storage and never logged.
- Quota and TTL are enforced server-side on every `validate_session` call.
- Audit entries contain summary metadata only — no tokens, passwords, or PII.
- Error responses are non-enumerating: `GUEST_INVALID_SESSION` is returned for both unknown and revoked tokens, and `convert_to_user` returns the same `AUTH_USER_EXISTS` error a regular registration would surface.
