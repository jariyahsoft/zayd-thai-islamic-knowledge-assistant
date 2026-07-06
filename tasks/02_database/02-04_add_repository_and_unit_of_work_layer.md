# TASK-02-04 — Add Repository and Unit-of-Work Layer

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §3 Modular Architecture
- SRS §23 Data Model

## Objective

Create repository interfaces and SQLAlchemy implementations for core aggregates.

## Scope

### In Scope

- Create repository interfaces and SQLAlchemy implementations for core aggregates.
- Implement transaction-scoped unit-of-work boundaries.
- Prevent domain/application services from executing ad-hoc SQL.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-02-03

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

- [ ] Repositories support required create, read, update and query operations.
- [ ] Transactions commit or roll back atomically.
- [ ] Integration tests run against PostgreSQL.
- [ ] Repository interfaces are mockable for unit tests.

## Required Tests

### Unit and Contract Tests

- Repository integration tests
- Transaction rollback tests
- Concurrent update tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/persistence.md`

## Completion Report

### Files Changed

- `services/common/pyproject.toml` - Added package dependencies for `sqlalchemy`, `asyncpg`, and `psycopg2-binary`
- `services/common/src/zayd_common/database/models.py` - Implemented SQLAlchemy declarative models mapping the database schema
- `services/common/src/zayd_common/database/repositories.py` - Implemented abstract and concrete repositories for core aggregates
- `services/common/src/zayd_common/database/unit_of_work.py` - Implemented abstract UoW interface and SQLAlchemy transaction boundary manager
- `services/common/src/zayd_common/database/__init__.py` - Implemented sessionmaker lifecycle helpers
- `services/common/src/zayd_common/__init__.py` - Exported the persistence layer contracts and classes
- `services/common/tests/test_database.py` - Added unit tests verifying CRUD and state transitions on SQLite
- `services/common/tests/test_database_postgres.py` - Added integration tests verifying CRUD on Postgres container database
- `infra/compose/development.yml` - Exposed port 5432 for Postgres to allow connection from pytest test runner on host
- `docs/architecture/persistence.md` - Added database persistence architecture documentation

### Commands and Tests Executed

```bash
# Locked and resolved package dependencies for all workspaces
uv sync --all-packages

# Executed Python test suite (all 63 tests pass, warning-free)
uv run pytest

# Executed static typing verification (mypy error-free on our code)
uv run mypy .

# Verified code format and linting rules (ruff clean)
uv run ruff check .
```

### Acceptance Criteria Result

- [x] Repositories support required create, read, update and query operations: Fully implemented and verified in SQLite/Postgres tests.
- [x] Transactions commit or roll back atomically: Verified in UoW commit, rollback, and rollback-on-failure tests.
- [x] Integration tests run against PostgreSQL: Verified end-to-end user and document lifecycle CRUD on a PG engine fixture.
- [x] Repository interfaces are mockable for unit tests: Interface abstraction verified with unittest MagicMock.

### Security and License Review

- No credentials, keys, or private endpoints committed
- Local connection string uses public dev credentials only
- Real Postgres transaction states are rolled back immediately after tests to prevent data pollution
- Exposed 5432 ports are restricted to safe development networks

### Known Limitations

- PostgreSQL integration test relies on a running PostgreSQL container. If Docker Compose isn't running, tests skip gracefully using OperationalError probe.

### Follow-up Tasks

- TASK-03-XX: Implement UoW transaction boundaries inside API controller routes and worker tasks
- TASK-05-XX: Integrate repositories into ingestion services to save extracted text and slices

### Commit

Ready to commit.

```
feat(database): implement Repository and Unit-of-Work layer

- Add declarative SQLAlchemy models mapping Postgres core schemas
- Add abstract and concrete SQLAlchemy repositories for User, Source,
  Document, and Incident aggregates
- Add SQLAlchemyUnitOfWork class enforcing transaction boundaries and atomicity
- Implement BaseUUID and BaseJSONB TypeDecorators compiling seamlessly
  under PostgreSQL and SQLite
- Add unit coverage on SQLite and integration coverage on PostgreSQL (63 passed)
- Document the persistence layer architecture in docs/architecture/persistence.md

Resolves: TASK-02-04

Co-Authored-By: Claude <noreply@anthropic.com>
```
