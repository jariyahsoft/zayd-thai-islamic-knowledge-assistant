# Disaster recovery runbook

## Targets and ownership

The initial target is RPO 24 hours and RTO 8 hours. The incident commander authorizes recovery;
the backup operator retrieves artifacts; the database and storage operators restore isolated
targets; security verifies audit evidence and access; the application owner approves cutover.

## Procedure

1. Declare the incident, freeze destructive changes, create a trace/change ID, and preserve logs.
2. Identify the newest off-site encrypted artifact from before the incident. Verify its adjacent
   SHA-256 file without decrypting it.
3. Provision isolated PostgreSQL and private object storage with separate credentials. Do not
   overwrite production during diagnosis.
4. Follow the restore drill in `backup-restore.md`. Stop on any checksum, decryption, database,
   object-store, or permission error.
5. Run migrations only when the restored application release explicitly requires them. Verify
   foreign keys, role grants, audit-chain checkpoints, document/object counts, and representative
   application workflows without exposing private content.
6. Security and application owners review results. Use a documented change window to redirect
   traffic; retain the prior environment for rollback and monitor errors, health, and audit events.
7. Close the incident only after recording achieved RPO/RTO, data gaps, validation evidence,
   approvals, and follow-up actions.

If no valid artifact exists, evidence conflicts, or the restored database and object store do not
agree, do not improvise or silently discard records. Keep the service unavailable or read-only as
appropriate, escalate to security/data owners, and document the exception.

## Routine controls

- Review daily job and off-site-copy failures each day.
- Test restore monthly in an isolated environment.
- Test loss of the primary region/failure domain at least annually.
- Rotate backup credentials and encryption keys under the secret-management procedure; retain old
  decryption keys for the corresponding retention window.
- Review retention, legal hold, audit retention, and licensed-source obligations before deletion.
