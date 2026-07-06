# TASK-02-05 — Add Demo Seed Data

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- FR-OSS-005
- FR-OSS-006
- SRS §42 Data Contribution Workflow

## Objective

Create repeatable seed commands for demo users, roles, sources, licenses, documents and citations.

## Scope

### In Scope

- Create repeatable seed commands for demo users, roles, sources, licenses, documents and citations.
- Use synthetic or clearly redistributable demonstration content only.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-02-04

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

- [ ] Seed command is idempotent.
- [ ] No restricted religious corpus or personal data is included.
- [ ] Demo data is visibly labelled as non-authoritative.
- [ ] Seeded accounts require credential rotation or generated passwords.

## Required Tests

### Unit and Contract Tests

- Run seed twice
- License-manifest validation
- Secret scan of seed fixtures

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `database/seeds/README.md`
- `docs/development/demo-data.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/database/seeding.py`
- `database/seeds/seed.py`
- `database/seeds/README.md`
- `docs/development/commands.md`
- `docs/development/demo-data.md`
- `services/common/tests/test_seeding.py`
- `Makefile`
- `tasks/02_database/02-05_add_demo_seed_data.md`
- `tasks/00_task_index.md`
- `tasks/03_auth/03-01_implement_user_authentication.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_seeding.py`
- `uv run pytest services/common/tests/test_database_postgres.py`
- `uv run pytest database/tests/test_initial_migration.py`
- `uv run ruff check services/common/src/zayd_common/database/seeding.py services/common/tests/test_seeding.py database/seeds/seed.py`
- `uv run ruff format --check services/common/src/zayd_common/database/seeding.py services/common/tests/test_seeding.py database/seeds/seed.py`
- Secret scan of seed fixtures under `services/common/src/zayd_common/database/seeding.py`, `database/seeds/seed.py`, `database/seeds/README.md`, and `docs/development/demo-data.md`
- License-manifest validation via `services/common/tests/test_seeding.py::test_license_manifest_validation`

### Acceptance Criteria Result

- [x] Seed command is idempotent.
- [x] No restricted religious corpus or personal data is included.
- [x] Demo data is visibly labelled as non-authoritative.
- [x] Seeded accounts require credential rotation or generated passwords.

### Security and License Review

- Demo content is synthetic and redistribution-safe.
- Seed labels make the demo nature explicit.
- Generated passwords are temporary and printed only on the first run.
- Secret markers were scanned out of the seed implementation and docs.

### Known Limitations

- `make seed-demo` expects a reachable PostgreSQL database. Use the development stack or set `DATABASE_URL` for a custom target.

### Follow-up Tasks

- Mark `TASK-03-01` as `READY` now that EPIC-02 is complete.

### Commit

- Pending
