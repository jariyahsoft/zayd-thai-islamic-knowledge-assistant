# Authorization API

Zayd authorization is enforced server-side through bearer-token authentication plus RBAC permission checks. Clients may use these APIs to inspect the current principal or request protected role/authorization mutations, but clients must not treat hidden UI controls as enforcement.

## Error shape

Authorization failures use the stable API error envelope:

```json
{
  "error": {
    "code": "RBAC_FORBIDDEN",
    "message": "Forbidden."
  }
}
```

Common codes:

| Code | HTTP status | Meaning |
|---|---:|---|
| `AUTH_UNAUTHENTICATED` | 401 | Missing, invalid, or expired bearer token. |
| `RBAC_FORBIDDEN` | 403 | Caller is authenticated but lacks the required permission. |
| `RBAC_UNKNOWN_PERMISSION` | 400 | Server-side permission name is not recognized. |
| `RBAC_UNKNOWN_ROLE` | 404 | Requested role is not recognized. |
| `RBAC_UNKNOWN_USER` | 404 | Target user is unavailable for role changes. |
| `RBAC_SEPARATION_OF_DUTIES` | 403 | The action violates separation-of-duties policy. |
| `RBAC_LAST_ADMIN` | 409 | The action would remove the final active admin assignment. |

Responses intentionally avoid exposing secrets, credentials, document contents, or full request payloads.

## Current principal

```http
GET /auth/me
Authorization: Bearer <access_token>
```

Returns the authenticated user ID, email, effective roles, and effective permissions:

```json
{
  "id": "2d0e6b19-f5fe-4f3d-a77f-181a2c0d65c4",
  "email": "user@example.com",
  "roles": ["user"],
  "permissions": ["conversations.manage_own", "feedback.create", "sessions.revoke_own", "users.read_self"]
}
```

## Role administration

Role administration endpoints require `users.roles.manage` and audit successful role changes.

### Grant a role

```http
POST /admin/users/roles/grant
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

```json
{
  "user_id": "58d9d137-1289-4da2-941b-17f338dd0836",
  "role_name": "reviewer"
}
```

Response:

```json
{
  "status": "ok",
  "changed": true
}
```

`changed` is `false` when the user already has the role.

### Revoke a role

```http
POST /admin/users/roles/revoke
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

```json
{
  "user_id": "58d9d137-1289-4da2-941b-17f338dd0836",
  "role_name": "reviewer"
}
```

The API refuses to revoke the last active admin assignment and returns `RBAC_LAST_ADMIN`.

## Document approval authorization check

Later document-workflow endpoints must use the same service guard. The current authorization check endpoint exercises the policy directly:

```http
POST /authorization/documents/approve
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "document_created_by": "58d9d137-1289-4da2-941b-17f338dd0836"
}
```

Required permission: `documents.approve`.

If the actor is also the uploader/creator, the service returns `RBAC_SEPARATION_OF_DUTIES` to prevent self-approval of restricted work.

## Bootstrap endpoint

```http
POST /admin/rbac/bootstrap
Authorization: Bearer <admin_access_token>
```

This protected endpoint idempotently ensures system roles and permissions exist. Normal environments should rely on migration `0004_rbac_seed`; this endpoint is for trusted maintenance flows after an initial admin has already been provisioned.

## Audit behavior

- Role grants emit `rbac.role.grant` audit entries.
- Role revocations emit `rbac.role.revoke` audit entries.
- Denied permission checks emit `rbac.permission.check` with reason `permission_missing`.
- Separation-of-duties denials emit `rbac.separation_of_duties.documents.approve`.

Audit summaries include compact identifiers such as role names and target user IDs. They must not include tokens, credentials, full documents, full conversations, or production payloads.
