# TASK-07-04 — Vector Search with pgvector

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-RET-004
- SRS §7.3 Database

## Objective

Implement pgvector indexing and filtered similarity search.

## Scope

### In Scope

- Implement pgvector indexing and filtered similarity search.
- Support embedding-model/version isolation and query timeout.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-02

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

- [x] Search never mixes incompatible embedding spaces.
- [x] Published/status/license filters are enforced in the query.
- [x] Index choice and maintenance process are documented.

## Required Tests

### Unit and Contract Tests

- Similarity integration tests
- Filter enforcement tests
- Timeout/load smoke tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/pgvector-search.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/retrieval/src/zayd_service_retrieval/vector_search.py` (new)
- `services/retrieval/src/zayd_service_retrieval/__init__.py`
- `services/retrieval/tests/test_vector_search.py` (new)
- `services/common/src/zayd_common/database/models.py`
- `database/migrations/0011_pgvector_search.up.sql` (new)
- `database/migrations/0011_pgvector_search.down.sql` (new)
- `database/migrations/README.md`
- `docs/architecture/pgvector-search.md` (new)
- `tasks/07_retrieval/07-04_vector_search_with_pgvector.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/retrieval/tests/test_vector_search.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run pytest services/retrieval/tests/test_full_text_search.py services/retrieval/tests/test_vector_search.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/common/src/zayd_common/database/models.py services/retrieval/src/zayd_service_retrieval/vector_search.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_vector_search.py`
- `uv run mypy services/common/src/zayd_common/database/models.py services/retrieval/src/zayd_service_retrieval/vector_search.py services/retrieval/src/zayd_service_retrieval/__init__.py --ignore-missing-imports`
- `python3 -m py_compile services/common/src/zayd_common/database/models.py services/retrieval/src/zayd_service_retrieval/vector_search.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_vector_search.py && git diff --check`

### Acceptance Criteria Result

- Passed. Vector search filters by model configuration, provider and dimension before ranking, rejects provider and dimension mismatches, and never returns embeddings from another model space.
- Passed. Published document/version/chunk, active source, active embedding, and license/embedding-permission gates are enforced in SQL query construction.
- Passed. HNSW cosine index choice, timeout handling, embedding-space isolation and maintenance process are documented in `docs/architecture/pgvector-search.md`.

### Security and License Review

- No secrets, production data, PHI, or restricted religious datasets were introduced.
- Retrieval fails closed for disabled providers/models, unpublished chunks, non-published document versions, inactive sources, and ineligible licenses.
- Telegram credentials provided in user text were not written to files or embedded in tool calls.

### Known Limitations

- SQLite tests validate behavior and query contracts; production pgvector performance still requires applying migrations in a PostgreSQL environment.
- Persisted retrieval-run/result traces are left to the hybrid retrieval task that combines score components.

### Follow-up Tasks

- TASK-07-05 Hybrid Search should compose vector and full-text scores and persist retrieval traces.

### Commit

- Focused commit created for TASK-07-04.
