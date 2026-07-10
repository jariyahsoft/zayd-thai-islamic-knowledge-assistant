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
| `0008_document_review_api` | `0008_document_review_api.up.sql`, `0008_document_review_api.down.sql` | Document review revisions, decisions, comments and optimistic task row versions for TASK-06-02 |
| `0009_scholar_approval_workflow` | `0009_scholar_approval_workflow.up.sql`, `0009_scholar_approval_workflow.down.sql` | Scholar approval, expiry and revocation records for TASK-06-03 |
| `0010_full_text_search` | `0010_full_text_search.up.sql`, `0010_full_text_search.down.sql` | Retrieval reference/full-text indexes and filter support for TASK-07-03 |
| `0011_pgvector_search` | `0011_pgvector_search.up.sql`, `0011_pgvector_search.down.sql` | pgvector embedding-space and filtered vector search indexes for TASK-07-04 |
| `0012_user_app_preferences` | `0012_user_app_preferences.up.sql`, `0012_user_app_preferences.down.sql` | User answer length, Arabic visibility, and history mode preferences for TASK-09-04 |
| `0013_saved_answers` | `0013_saved_answers.up.sql`, `0013_saved_answers.down.sql` | User saved-answer bookmarks referencing answers for TASK-09-06 |
| `0014_feedback_review_queue` | `0014_feedback_review_queue.up.sql`, `0014_feedback_review_queue.down.sql` | Feedback queue assignment, classification, resolution, and reviewer permission grant for TASK-11-02 |
| `0015_incident_management` | `0015_incident_management.up.sql`, `0015_incident_management.down.sql` | Incident ownership, idempotency, alert status, and append-only timeline for TASK-11-03 |
| `0016_answer_invalidation` | `0016_answer_invalidation.up.sql`, `0016_answer_invalidation.down.sql` | Append-only answer invalidation history and notification status for TASK-11-04 |
| `0017_evaluation_case_schema` | `0017_evaluation_case_schema.up.sql`, `0017_evaluation_case_schema.down.sql` | Versioned evaluation case contracts, visibility metadata, and evaluation RBAC for TASK-12-01 |

Use `scripts/migrate.sh up`, `scripts/migrate.sh down`, or `MIGRATION_ACTION=<up|down|reset> make migrate` for development/test execution. The `up` action is idempotent when `schema_migrations` already contains a migration version.

Downgrade files are for development and test environments only unless a production rollback plan has been approved.
