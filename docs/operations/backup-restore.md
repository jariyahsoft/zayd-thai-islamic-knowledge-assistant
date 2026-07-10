# Backup and restore

Zayd uses a daily encrypted recovery bundle for PostgreSQL (including roles and grants), private
object storage, and non-secret governance, policy, and license configuration. Database rows remain
the source of truth for object metadata. The initial recovery objectives are RPO 24 hours and RTO
8 hours.

## Backup configuration

Run `infra/backup/backup.sh` as a dedicated, least-privileged backup identity. Required variables
are `DATABASE_URL`, `S3_BUCKET`, and `BACKUP_ENCRYPTION_KEY_FILE`. The key file must be supplied by
the host secret manager and must never be stored in the repository or backup destination.

Optional controls are:

- `BACKUP_ROOT` (default `/var/backups/zayd`)
- `BACKUP_RETENTION_DAYS` (default `30`)
- `OFFSITE_S3_URI` for an encrypted copy in a separate account or failure domain
- `S3_ENDPOINT` for an S3-compatible provider
- `BACKUP_CONFIG_PATHS`, a whitespace-separated allow-list of non-secret paths
- `BACKUP_ACTOR`, `BACKUP_TRACE_ID`, and `BACKUP_AUDIT_DIR`

Use separate read-only database/object-store credentials for backup. Enable bucket versioning or
object lock at the off-site destination. The systemd timer in `infra/backup/` provides the daily
schedule; the operator must connect service failure to the approved alerting channel. Never put
credentials in the unit or environment file committed to source control.

## Restore drill

Restore only into a network-isolated environment with fresh database and object-storage targets:

```bash
RESTORE_ENVIRONMENT=isolated \
RESTORE_DATABASE_URL='<isolated database URL>' \
RESTORE_S3_BUCKET='<empty isolated bucket>' \
BACKUP_ENCRYPTION_KEY_FILE='<secret-mounted file>' \
infra/backup/restore.sh /var/backups/zayd/zayd-YYYYMMDDTHHMMSSZ.tar.gpg
```

The script verifies the encrypted artifact and every payload file before changing state, restores
roles before the custom PostgreSQL dump, restores object data, and checks both dependencies. The
target credentials must not have access to production. Inspect `operations.jsonl`, validate the
audit hash chain against its off-database checkpoint, compare database object keys to the isolated
bucket inventory, and run application smoke/RBAC tests. Record drill owner, trace ID, artifact,
start/end time, counts, exceptions, and approval in the incident/change system.

Run a drill at least monthly and before the 1.0 production gate. A successful script run is not
production approval; security and operations reviewers must sign off on credentials, restoration
permissions, referential integrity, and application-level consistency.
