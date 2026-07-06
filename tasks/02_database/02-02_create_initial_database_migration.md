# TASK-02-02 — Create Initial Database Migration

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §23 Data Model
- FR-OSS-008
- NFR-BCK-001

## Objective

Create the initial PostgreSQL migration for the approved schema.

## Scope

### In Scope

- Create the initial PostgreSQL migration for the approved schema.
- Enable required extensions including pgvector where appropriate.
- Provide reversible downgrade steps for development and test environments.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-02-01

## Expected Files

- Implementation files under the relevant `02_database` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use PostgreSQL-compatible types and explicit constraints.
- Keep domain logic outside migration files.
- Design for versioning and auditability.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect referential integrity and sensitive fields.

## Acceptance Criteria

- [ ] Migration succeeds from an empty database.
- [ ] Downgrade restores the prior state without leaving unmanaged objects.
- [ ] Indexes exist for foreign keys and documented high-frequency queries.
- [ ] Migration is deterministic and passes migration-lint checks.

## Required Tests

### Unit and Contract Tests

- Upgrade from empty database
- Downgrade and re-upgrade
- Constraint and index integration tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `database/migrations/README.md`
- `docs/development/migrations.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `database/migrations/0001_initial_core_domain.up.sql` — initial PostgreSQL/pgvector schema migration with extensions, enums, tables, constraints, indexes, triggers and migration tracking.
- `database/migrations/0001_initial_core_domain.down.sql` — development/test rollback that drops migration-owned tables, functions and enum types in dependency order.
- `scripts/migrate.sh` — development/test migration runner supporting `up`, `down` and `reset`, preferring Docker Compose PostgreSQL and falling back to host `psql`.
- `Makefile` — wires `make migrate` to `scripts/migrate.sh` with `MIGRATION_ACTION` support.
- `.gitignore` — keeps backup SQL artifacts ignored while explicitly allowing tracked SQL migrations under `database/migrations/`.
- `database/tests/test_initial_migration.py` — integration tests for static migration linting, upgrade, downgrade, re-upgrade, constraints/indexes and active-embedding failure behavior.
- `database/migrations/README.md` — migration index and execution notes.
- `docs/development/migrations.md` — developer migration workflow, safety rules and verification notes.
- `tasks/00_task_index.md`, `tasks/02_database/02-02_create_initial_database_migration.md`, `tasks-update.md` — task status and completion records.

### Commands and Tests Executed

- `docker compose up -d postgres` — PostgreSQL/pgvector service running.
- `MIGRATION_ACTION=reset make migrate` — passed; downgraded and re-applied the initial migration on the development database.
- `make migrate` — passed; confirmed idempotent no-op when `0001_initial_core_domain` is already recorded.
- `bash -n scripts/migrate.sh` — passed.
- `uv run pytest database/tests/test_initial_migration.py` — passed, 4 tests.
- `uv run pytest database/tests/test_core_domain_schema.py database/tests/test_initial_migration.py` — passed, 13 tests.
- `uv run ruff check database/tests/test_core_domain_schema.py database/tests/test_initial_migration.py` — passed.
- `uv run ruff format --check database/tests/test_core_domain_schema.py database/tests/test_initial_migration.py` — passed.
- `uv run mypy database/tests/test_core_domain_schema.py database/tests/test_initial_migration.py` — passed.
- TASK-02-02 secret marker scan — passed.

### Acceptance Criteria Result

- [x] Migration succeeds from an empty database.
- [x] Downgrade restores the prior state without leaving migration-owned tables/functions/types unmanaged.
- [x] Indexes exist for foreign keys and documented high-frequency queries.
- [x] Migration is deterministic and passes migration-lint checks.

### Security and License Review

- No secrets, credentials, production data or restricted religious content were introduced.
- Migration SQL creates structure only; it does not seed user data, document content or provider credentials.
- Provider tables store secret references only, not secret values.
- License-critical content and embedding boundaries are enforced by constraints/triggers where feasible.
- Rollback is documented as development/test only; production rollback requires backup/restore policy and approval.
- No third-party code or new dependencies were added.

### Known Limitations

- The initial embedding vector dimension is fixed at 1536 for the first migration; future model-specific dimensions may require additional migrations.
- Some state-machine and RBAC behavior remains service-level domain logic and is deferred to TASK-02-03 and later API/auth tasks.
- The down migration intentionally leaves PostgreSQL extensions installed because extensions may be shared capabilities in a database.
- `scripts/migrate.sh` is a lightweight development/test runner, not a production deployment migration framework.

### Follow-up Tasks

- TASK-02-03 — Implement Domain Enums and State Machines.
- TASK-02-04 — Add Repository and Unit-of-Work Layer.
- TASK-07-04 — Vector Search with pgvector.
- EPIC-13 — Production backup/restore and migration hardening.

### Commit

- Focused TASK-02-02 commit created during finalization with message `feat(database): add initial core domain migration`.
