# TASK-07-03 — Full-text Search

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-RET-002
- FR-RET-003
- FR-RET-006

## Objective

Implement PostgreSQL full-text/exact search suitable for Thai, Arabic references and metadata filters.

## Scope

### In Scope

- Implement PostgreSQL full-text/exact search suitable for Thai, Arabic references and metadata filters.
- Return explainable score components.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-01

## Expected Files

- Implementation files under the relevant `07_retrieval` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Record retrieval configuration and model/index versions.
- Enforce status/license filters inside data-access queries, not after retrieval.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Do not allow filters to be bypassed through query expansion or provider fallback.

## Acceptance Criteria

- [x] Only published chunks are searched.
- [x] Exact canonical references receive deterministic handling.
- [x] Filters support language, madhhab, source type and license eligibility.

## Required Tests

### Unit and Contract Tests

- Thai/Arabic query fixtures
- Canonical reference tests
- Filter and visibility tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/full-text-search.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/retrieval/src/zayd_service_retrieval/full_text_search.py`
- `services/retrieval/src/zayd_service_retrieval/__init__.py`
- `services/retrieval/tests/test_full_text_search.py`
- `database/migrations/0010_full_text_search.up.sql`
- `database/migrations/0010_full_text_search.down.sql`
- `database/migrations/README.md`
- `docs/architecture/full-text-search.md`
- `tasks/07_retrieval/07-03_full_text_search.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/retrieval/tests/test_full_text_search.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/retrieval/src/zayd_service_retrieval/full_text_search.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/src/zayd_service_retrieval/service.py services/retrieval/tests/test_full_text_search.py database/migrations/README.md`
- `uv run mypy services/retrieval/src/zayd_service_retrieval/full_text_search.py services/retrieval/src/zayd_service_retrieval/service.py --ignore-missing-imports`
- `python3 -m py_compile services/retrieval/src/zayd_service_retrieval/full_text_search.py services/retrieval/src/zayd_service_retrieval/service.py services/retrieval/tests/test_full_text_search.py && git diff --check`

### Acceptance Criteria Result

- Passed. Search only returns chunks that remain published and whose document/version/source/license state is retrieval-eligible.
- Passed. Exact canonical reference matches are scored deterministically ahead of full-text matches, with prefix handling preserved for structured references.
- Passed. Query filters cover language, madhhab, source type, license status, and source reliability constraints.

### Security and License Review

- Search visibility is enforced in the query path rather than post-filtered in application code.
- The retrieval filter path fails closed for ineligible licenses, unpublished versions, unpublished chunks, and inactive sources.

### Known Limitations

- SQLite tests validate behavior and scoring rules, while PostgreSQL-specific `tsvector` and trigram performance depends on applying the new migration in a Postgres environment.

### Follow-up Tasks

- TASK-07-04 Vector Search with pgvector
- TASK-07-05 Hybrid Search

### Commit

- Focused commit `feat(retrieval): add full-text search service`
