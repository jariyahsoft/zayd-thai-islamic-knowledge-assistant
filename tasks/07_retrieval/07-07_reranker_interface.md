# TASK-07-07 — Reranker Interface

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-RET-008
- SRS §29 Model Routing

## Objective

Define local/external reranker adapters with timeout, capability metadata and safe fallback to hybrid ranking.

## Scope

### In Scope

- Define local/external reranker adapters with timeout, capability metadata and safe fallback to hybrid ranking.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-05

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

- [x] Reranker failures do not break retrieval.
- [x] Scores and model versions are stored.
- [x] Provider data-sharing restrictions are respected.

## Required Tests

### Unit and Contract Tests

- Adapter contract tests
- Timeout/fallback tests
- Score trace tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/development/reranker-providers.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/retrieval/src/zayd_service_retrieval/reranker.py` (new)
- `services/retrieval/src/zayd_service_retrieval/__init__.py`
- `services/retrieval/tests/test_reranker.py` (new)
- `docs/development/reranker-providers.md` (new)
- `tasks/07_retrieval/07-07_reranker_interface.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/retrieval/tests/test_reranker.py -v`
- `uv run pytest services/retrieval/tests/test_full_text_search.py services/retrieval/tests/test_vector_search.py services/retrieval/tests/test_hybrid_search.py services/retrieval/tests/test_query_expansion.py services/retrieval/tests/test_reranker.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/retrieval/src/zayd_service_retrieval/query_expansion.py services/retrieval/src/zayd_service_retrieval/reranker.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_query_expansion.py services/retrieval/tests/test_reranker.py`
- `uv run mypy services/retrieval/src/zayd_service_retrieval/query_expansion.py services/retrieval/src/zayd_service_retrieval/reranker.py services/retrieval/src/zayd_service_retrieval/__init__.py --ignore-missing-imports`
- `python3 -m py_compile services/retrieval/src/zayd_service_retrieval/query_expansion.py services/retrieval/src/zayd_service_retrieval/reranker.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_query_expansion.py services/retrieval/tests/test_reranker.py && git diff --check`

### Acceptance Criteria Result

- Passed. Provider errors, disabled reranking, timeout overruns, and blocked external data-sharing all fall back to hybrid ranking instead of breaking retrieval.
- Passed. Successful reranking records score, final rank, provider/model identifiers, provider version, model revision, and interface version; matching `retrieval_results` rows are updated when a retrieval run is present.
- Passed. External providers are not called when data-sharing approval is required but unavailable.

### Security and License Review

- No secrets, production data, PHI, restricted religious datasets, or third-party code were introduced.
- The default reranker is local and deterministic; external providers are blocked unless provider metadata permits data sharing.
- Reranking does not create new retrieval candidates and therefore cannot bypass SQL-level publication/license filters from hybrid search.

### Known Limitations

- The local keyword reranker is a deterministic fallback, not a semantic model.
- Production external reranker adapters remain future provider-SDK/plugin work.

### Follow-up Tasks

- TASK-07-08 Evidence Sufficiency Engine should consume reranker scores alongside hybrid score components.

### Commit

- Focused commit created for TASK-07-07.
