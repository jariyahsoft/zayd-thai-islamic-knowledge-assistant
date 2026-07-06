# Audit Logging

Zayd writes append-only audit records for sensitive authentication, authorization, document, review, publication, provider, prompt, policy, and security actions.

## Scope

Audit events capture safe metadata only:

- actor user ID when available
- action name, such as `auth.login`, `rbac.role.grant`, `documents.publish`, `providers.disable`, `prompts.update`, or `policies.update`
- resource type and resource ID when available
- outcome: `success`, `failure`, `denied`, or `error`
- request ID and trace ID
- short before/after summaries
- sanitized source context
- hash-chain metadata

Audit records must not include passwords, bearer tokens, refresh tokens, MFA secrets, recovery codes, provider API keys, full user conversations, restricted religious content, hidden chain-of-thought, or raw payload dumps.

## Append-only enforcement

Application code treats `audit_logs` as immutable:

- ORM update and delete operations are rejected before flush.
- The PostgreSQL migration for TASK-03-05 replaces the generic `updated_at` trigger with database triggers that reject `UPDATE` and `DELETE` on `audit_logs`.
- Application roles are granted only read/export permissions for audit data; no role has an application permission to update or delete audit rows.

Direct database superusers can still bypass application safeguards. Production deployments must therefore restrict database superuser access, use separate migration/operator credentials, and monitor privileged database activity.

## Tamper evidence

Each audit row stores:

- `hash_algorithm`, currently `sha256`
- `previous_hash`, the hash of the preceding audit row by creation order
- `content_hash`, a SHA-256 hash over canonical audit metadata and `previous_hash`

This creates a hash chain. Deleting or changing a historical row breaks the continuity or content hash for subsequent verification. Production operators should periodically export hash-chain checkpoints to off-database storage, such as write-once object storage, a SIEM, or another append-only archive.

## Redaction

The audit model redacts sensitive summary keys before hashing and persistence. Keys containing markers such as `password`, `token`, `secret`, `authorization`, `api_key`, `credential`, `mfa_secret`, or `recovery_code` are stored as `[REDACTED]`.

Callers should still provide only minimal summaries. Do not rely on redaction to make raw request bodies safe for audit storage.

## Query and export

Authorized Admin/Auditor users can read audit entries through:

- `GET /admin/audit-logs`
- `GET /admin/audit-logs/export`

Both endpoints are protected by RBAC. The list endpoint requires `audit.read`; export requires `audit.export`. Export returns newline-delimited JSON for bounded operational review and archival workflows.

## Implementation notes

- Use `AuditService.record(...)` for new domain services that do not already have a local audit helper.
- Existing auth, guest, MFA, and RBAC flows set `request_id` from the inbound request ID/trace ID and write compact summaries.
- Future document, review, publication, provider, prompt, and policy services must record sensitive mutations with safe before/after summaries.
