# Database Migrations

Owner category: database maintainers.

Forward migrations and documented rollback plans belong here.

## Current migrations

| Version | Direction files | Description |
|---|---|---|
| `0001_initial_core_domain` | `0001_initial_core_domain.up.sql`, `0001_initial_core_domain.down.sql` | Initial PostgreSQL core-domain schema for TASK-02-02 |
| `0002_auth_token_rotation` | `0002_auth_token_rotation.up.sql`, `0002_auth_token_rotation.down.sql` | Refresh-token rotation, password reset tokens, and auth rate-limit buckets for TASK-03-01 |
| `0003_guest_sessions` | `0003_guest_sessions.up.sql`, `0003_guest_sessions.down.sql` | Anonymous guest sessions with TTL and message quota for TASK-03-02 |
| `0004_rbac_seed` | `0004_rbac_seed.up.sql`, `0004_rbac_seed.down.sql` | RBAC system permissions, roles, and permission matrix for TASK-03-03 |
| `0005_mfa_privileged` | `0005_mfa_privileged.up.sql`, `0005_mfa_privileged.down.sql` | MFA secrets, recovery codes, and challenges for TASK-03-04 |
| `0006_immutable_audit_logs` | `0006_immutable_audit_logs.up.sql`, `0006_immutable_audit_logs.down.sql` | Append-only hash-chained audit logs with request IDs for TASK-03-05 |
| `0007_review_tasks` | `0007_review_tasks.up.sql`, `0007_review_tasks.down.sql` | Review tasks table for TASK-05-07 |

Use `scripts/migrate.sh up`, `scripts/migrate.sh down`, or `MIGRATION_ACTION=<up|down|reset> make migrate` for development/test execution. The `up` action is idempotent when `schema_migrations` already contains a migration version.

Downgrade files are for development and test environments only unless a production rollback plan has been approved.
