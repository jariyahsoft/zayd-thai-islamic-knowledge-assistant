# User and Role Administration

The admin workspace now includes a Users and Roles section for `TASK-10-06`.

## What admins can do

- Search users by email or display name
- Filter by account status or role
- Grant roles
- Revoke roles
- Disable or re-enable accounts
- Revoke all active sessions for a selected user

## Final admin guard

The final active admin account is guarded in both UI messaging and server-side
enforcement.

- The UI marks the account as `Final active admin`
- Disabling that account is rejected by the API
- Revoking the last active `admin` role remains blocked by the RBAC service

This prevents accidental loss of recoverable admin access.

## Session revocation

Two flows revoke active sessions:

- explicit admin action through `POST /admin/users/{user_id}/sessions/revoke`
- automatic revocation when an account is disabled

Both flows also revoke refresh tokens for those sessions.

## Audit trail

The following actions write immutable audit entries:

- role grants
- role revocations
- account status changes
- admin-triggered session revocation

Audit summaries include compact operational metadata only and do not expose
credentials or session tokens.
