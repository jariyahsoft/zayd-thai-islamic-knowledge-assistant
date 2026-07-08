# TASK-07-02 — Embedding Provider Interface

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §9.2 Embedding Provider Interface
- FR-OSS-004

## Objective

Define embedding provider contracts and adapters for local and OpenAI-compatible services.

## Scope

### In Scope

- Define embedding provider contracts and adapters for local and OpenAI-compatible services.
- Track model ID, revision, dimensions and normalization settings.

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

- [x] Provider can be changed through configuration.
- [x] Dimension mismatches are detected before write/search.
- [x] Batching, timeout and retry behavior are documented and tested.

## Required Tests

### Unit and Contract Tests

- Provider contract tests
- Dimension mismatch tests
- Batch failure tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/development/embedding-providers.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/embeddings.py`
- `services/common/src/zayd_common/settings.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/tests/test_embeddings.py`
- `services/common/tests/test_settings_embeddings.py`
- `docs/development/embedding-providers.md`
- `tasks/07_retrieval/07-02_embedding_provider_interface.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_embeddings.py services/common/tests/test_settings_embeddings.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/common/src/zayd_common/embeddings.py services/common/src/zayd_common/settings.py services/common/src/zayd_common/__init__.py services/common/tests/test_embeddings.py services/common/tests/test_settings_embeddings.py services/retrieval/src/zayd_service_retrieval/service.py`
- `uv run mypy services/common/src/zayd_common/embeddings.py services/common/src/zayd_common/settings.py services/retrieval/src/zayd_service_retrieval/service.py --ignore-missing-imports`
- `python3 -m py_compile services/common/src/zayd_common/embeddings.py services/common/src/zayd_common/settings.py services/retrieval/src/zayd_service_retrieval/service.py services/common/tests/test_embeddings.py services/common/tests/test_settings_embeddings.py && git diff --check`

### Acceptance Criteria Result

- Passed. Embedding providers are selected from runtime configuration and support local or OpenAI-compatible adapters without changing call sites.
- Passed. `EmbeddingService` validates provider dimensions for document and query embeddings before downstream write/search operations.
- Passed. Documentation and tests cover batching, finite timeout, and bounded retry behavior for the OpenAI-compatible adapter.

### Security and License Review

- No secrets, production data, restricted religious datasets, or proprietary dependencies were introduced.
- Local mode remains available with no external provider requirement, and OpenAI-compatible mode fails closed when configuration or transport guarantees are invalid.

### Known Limitations

- The local provider is deterministic hashing for self-hosted compatibility, not a semantic model. Real vector storage and provider-backed re-embedding remain follow-up work.

### Follow-up Tasks

- TASK-07-04 Vector Search with pgvector
- TASK-07-05 Hybrid Search

### Commit

- Focused commit `feat(retrieval): add embedding provider interface`
