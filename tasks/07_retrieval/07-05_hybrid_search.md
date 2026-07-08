# TASK-07-05 — Hybrid Search

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-RET-005
- FR-RET-010

## Objective

Combine exact-reference, full-text, vector and source-reliability signals using configurable weights.

## Scope

### In Scope

- Combine exact-reference, full-text, vector and source-reliability signals using configurable weights.
- Record component scores for explainability and evaluation.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-03
- TASK-07-04

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

- [x] Weights are versioned and configurable.
- [x] Results are deterministic for fixed inputs/configuration.
- [x] Regression tests protect ranking of approved fixtures.

## Required Tests

### Unit and Contract Tests

- Ranking regression suite
- Weight configuration tests
- Missing-signal fallback tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/hybrid-search.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/retrieval/src/zayd_service_retrieval/hybrid_search.py` (new)
- `services/retrieval/src/zayd_service_retrieval/__init__.py`
- `services/retrieval/tests/test_hybrid_search.py` (new)
- `docs/architecture/hybrid-search.md` (new)
- `tasks/07_retrieval/07-05_hybrid_search.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/retrieval/tests/test_hybrid_search.py -v`
- `uv run pytest services/retrieval/tests/test_full_text_search.py services/retrieval/tests/test_vector_search.py services/retrieval/tests/test_hybrid_search.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/retrieval/src/zayd_service_retrieval/hybrid_search.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_hybrid_search.py`
- `uv run mypy services/retrieval/src/zayd_service_retrieval/hybrid_search.py services/retrieval/src/zayd_service_retrieval/__init__.py --ignore-missing-imports`
- `python3 -m py_compile services/retrieval/src/zayd_service_retrieval/hybrid_search.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_hybrid_search.py && git diff --check`

### Acceptance Criteria Result

- Passed. `HybridSearchWeights` is versioned, configurable, normalized, and rejects invalid all-zero, negative, or unversioned configurations.
- Passed. Ranking uses deterministic tie-breakers for fixed inputs and configuration.
- Passed. Regression tests cover default scoring, exact-weighted ranking, vector-weighted ranking, deterministic repeated runs, full-text-only fallback, invalid inputs, and license-filter visibility.

### Security and License Review

- No secrets, production data, PHI, restricted religious datasets, or new third-party code were introduced.
- Hybrid search composes full-text and vector services that enforce published/status/license filters inside data-access queries.
- Retrieval trace persistence stores score metadata and configuration versions, not credentials or source document payloads beyond already-returned retrieval result fields.

### Known Limitations

- Hybrid search persists returned paginated results only; full candidate-set persistence is left for future evaluation tooling if needed.
- Reranker and evidence sufficiency integration remain later retrieval tasks.

### Follow-up Tasks

- TASK-07-06 Multilingual Query Expansion can build on hybrid query orchestration.
- TASK-07-07 Reranker Interface can add reranker score components.

### Commit

- Focused commit created for TASK-07-05.
