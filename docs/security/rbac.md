# RBAC Security Model

Zayd uses server-side, action-based RBAC for protected API surfaces. UI hiding is never a security boundary; API handlers and domain services must call the RBAC dependency or service before returning protected data or executing sensitive mutations.

## Roles

| Role | Intended access |
|---|---|
| `guest` | Anonymous, TTL-bound sessions only; no back-office permissions. |
| `user` | Own profile/session actions, own conversations, and feedback submission. |
| `data_operator` | Document upload and pre-review document preparation. |
| `translator` | Document review/edit permissions for translation-oriented workflows. |
| `reviewer` | Document, answer, feedback, and evidence review. |
| `senior_scholar` | Religious-content approval, publishing, and answer invalidation. |
| `admin` | User, role, provider, license, prompt, model, and operational management. |
| `auditor` | Read/export audit and approved operational metadata without mutation rights. |
| `maintainer` | Provider, prompt, and model configuration for release operations. |

Registered accounts receive only the `user` role by default. Additional roles must be granted by an actor with `users.roles.manage`.

## Permission families

Permissions are stored as resource/action pairs and exposed as dotted strings such as `documents.approve`.

- `documents.*`: upload, edit, review, approve, publish, and archive document workflows.
- `answers.*`: review and invalidate generated answers.
- `providers.*`: read and manage provider configuration metadata.
- `licenses.*`: read and manage source license policy records.
- `users.*`: read accounts, manage accounts, and grant/revoke roles.
- `audit.*`: read and export audit logs.
- `feedback.*`: create, read, and manage feedback queues.
- `sessions.revoke_own` and `conversations.manage_own`: self-service user permissions.

The canonical matrix lives in `zayd_common.rbac.ROLE_PERMISSION_MATRIX` and is seeded by migration `0004_rbac_seed`.

## Enforcement rules

- Protected endpoints must depend on `require_permission(...)` or call `RbacService.require_permission`.
- Authorization failures return stable JSON errors without revealing whether another user or resource exists beyond the caller's authorization boundary.
- Role grants and revocations are audited through `audit_logs` with `resource_type='rbac'`.
- Permission-denied decisions are audited with the denied permission value, not request payload contents.
- Guests do not receive access tokens and cannot pass protected bearer-token dependencies.

## Separation of duties

Zayd enforces these RBAC guardrails in the service layer:

- A user cannot approve restricted document work they uploaded or created.
- The final active admin role assignment cannot be revoked.
- Auditors cannot mutate roles, providers, licenses, documents, prompts, models, or users.
- Reviewer roles can review but cannot publish without senior-scholar or admin-level permission.

Later workflow tasks must call the same service-level guards rather than duplicating authorization decisions in UI code.

## Auditing and privacy

RBAC audit entries record actor, action, resource, outcome, reason, trace ID, and compact before/after summaries. They must not include tokens, credentials, full document contents, full conversations, or production payloads.

## Operational notes

Run migrations through the standard development/test runner:

```bash
MIGRATION_ACTION=up make migrate
```

If an environment predates the RBAC seed migration, an admin with role-management permission may call the protected bootstrap endpoint after assigning an initial admin through a trusted local seed/admin process.
