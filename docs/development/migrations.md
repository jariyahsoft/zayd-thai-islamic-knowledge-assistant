# Database Migrations

Zayd database migrations live in `database/migrations/` and are executed by `scripts/migrate.sh` or `make migrate`.

## Current Migration

| Version | Description |
|---|---|
| `0001_initial_core_domain` | Initial PostgreSQL schema for the TASK-02-01 core domain design |

The initial migration creates:

- Required PostgreSQL extensions: `pgcrypto`, `citext`, `vector`.
- Domain enums for sources, language, madhhab, licenses, document state, review state, incidents, providers and evaluations.
- Tables for identity/RBAC, sources/licenses, documents/versions/pages/chunks, embeddings, reviews, citations, retrieval traces, conversations/messages/answers, feedback/incidents/audit, providers/models/prompts/policies and evaluations.
- Foreign-key, uniqueness, check and index definitions for the main access patterns.
- Integrity triggers for:
  - `updated_at` maintenance.
  - citation/chunk document-version consistency.
  - retrieval-result/chunk document-version consistency.
  - active embedding publication/license invariants.

## Running Migrations

Start PostgreSQL first:

```bash
make dev
```

Apply migrations:

```bash
make migrate
# or
scripts/migrate.sh up
```

`up` is idempotent for the initial migration: if `schema_migrations` already records `0001_initial_core_domain`, the runner exits successfully without reapplying the SQL.

Roll back the initial migration in development/test:

```bash
MIGRATION_ACTION=down make migrate
# or
scripts/migrate.sh down
```

Recreate the schema from scratch in development/test:

```bash
MIGRATION_ACTION=reset make migrate
# or
scripts/migrate.sh reset
```

## Safety Rules

- Downgrade is intended only for development and test databases.
- Production rollback requires a backup/restore plan and operational approval.
- Migration SQL must not contain business logic, secrets, production data or restricted religious content.
- Cross-row checks that PostgreSQL cannot express as plain constraints are implemented with narrow integrity triggers.
- Schema changes must be deterministic and must not depend on wall-clock data except migration timestamps recorded in `schema_migrations`.

## Local Verification

The migration is tested by `database/tests/test_initial_migration.py`, which verifies:

1. Upgrade from an empty PostgreSQL database.
2. Constraint and index presence.
3. Main success-path inserts.
4. A failure path for active embeddings that are not backed by published chunks and valid license permissions.
5. Downgrade and re-upgrade.

Run the focused tests with:

```bash
uv run pytest database/tests/test_initial_migration.py
```
