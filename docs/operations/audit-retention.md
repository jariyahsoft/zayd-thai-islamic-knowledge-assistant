# Audit Retention and Archival

Audit logs are operational security records. They support incident response, reviewer/admin accountability, provider and policy change review, and release-readiness checks.

## Retention targets

Initial self-host defaults:

- Keep audit rows in PostgreSQL for at least 365 days in production.
- Keep security-critical auth/RBAC/MFA/admin audit exports for at least 7 years when organizational policy permits.
- Keep development and test audit data only as long as required for debugging, then reset local databases normally.

Final production retention periods must be approved by the project owner and legal/privacy reviewers before public launch.

## Archival strategy

The application stores audit logs in PostgreSQL as append-only, hash-chained rows. PostgreSQL alone is not a complete external archive, because database superusers and backup operators may still alter or remove data.

Production deployments should add an external archival strategy before go-live:

1. Export recent audit rows on a fixed schedule through a dedicated auditor/admin service account.
2. Store exported NDJSON in private, encrypted object storage with bucket versioning or object lock enabled.
3. Store daily hash-chain checkpoints separately from the primary database.
4. Forward security-critical events to a SIEM or append-only log store when available.
5. Restrict delete permissions and require dual control for retention overrides.

## Access control

- `audit.read` allows bounded audit queries.
- `audit.export` allows bounded NDJSON export for review and archival.
- No application permission allows audit update or deletion.
- Auditors are read-only and cannot mutate users, roles, providers, licenses, documents, prompts, or models.

## Privacy and minimization

Audit records contain metadata and summaries, not raw production payloads. Operators must not export audit logs into public tickets, public repositories, chat tools, or unapproved analytics systems.

Exports may contain user IDs and administrative action metadata. Treat them as confidential operational data.

## Restore and verification

After database restore or incident response:

- Confirm `audit_logs` exists and append-only triggers are installed.
- Verify new audit inserts include `hash_algorithm`, `previous_hash`, and `content_hash`.
- Compare the latest restored hash-chain checkpoint against the external archive.
- Document any known gap or suspected tampering as a security incident.

## Known limitations

TASK-03-05 adds application and database-level append-only protections plus hash chaining. It does not provision object-lock storage, a SIEM, or a production retention scheduler. Those operational controls belong to later operations tasks.
