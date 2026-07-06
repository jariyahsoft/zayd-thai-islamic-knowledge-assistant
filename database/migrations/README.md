# Database Migrations

Owner category: database maintainers.

Forward migrations and documented rollback plans belong here.

## Current migrations

| Version | Direction files | Description |
|---|---|---|
| `0001_initial_core_domain` | `0001_initial_core_domain.up.sql`, `0001_initial_core_domain.down.sql` | Initial PostgreSQL core-domain schema for TASK-02-02 |

Use `scripts/migrate.sh up`, `scripts/migrate.sh down`, or `MIGRATION_ACTION=<up|down|reset> make migrate` for development/test execution. The `up` action is idempotent when `schema_migrations` already contains `0001_initial_core_domain`.

Downgrade files are for development and test environments only unless a production rollback plan has been approved.
