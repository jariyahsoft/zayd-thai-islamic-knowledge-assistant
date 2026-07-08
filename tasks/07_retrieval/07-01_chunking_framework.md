# TASK-07-01 — Chunking Framework

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §14.3 Chunking
- FR-ING-013

## Objective

Implement versioned chunking strategies for Quran verse, hadith, fiqh issue, heading section, paragraph, table and fixed-window fallback.

## Scope

### In Scope

- Implement versioned chunking strategies for Quran verse, hadith, fiqh issue, heading section, paragraph, table and fixed-window fallback.
- Retain page, section, canonical reference and optional surrounding context.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-06 complete

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

- [x] Every chunk maps to an immutable published document version.
- [x] Strategy and version are recorded.
- [x] Chunk boundaries preserve semantic units for supported content types.

## Required Tests

### Unit and Contract Tests

- Golden chunk fixtures
- Boundary/overlap tests
- Reference preservation tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/chunking.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/chunking.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/src/zayd_common/document_publishing.py`
- `services/common/tests/test_chunking.py`
- `services/common/tests/test_document_publishing.py`
- `docs/architecture/chunking.md`
- `docs/architecture/publishing-pipeline.md`
- `tasks/07_retrieval/07-01_chunking_framework.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_chunking.py -v`
- `uv run pytest services/common/tests/test_chunking.py services/common/tests/test_document_publishing.py services/api/tests/test_document_review_api.py -v`
- `uv run ruff check services/common/src/zayd_common/chunking.py services/common/src/zayd_common/document_publishing.py services/common/src/zayd_common/__init__.py services/common/tests/test_chunking.py services/common/tests/test_document_publishing.py`
- `uv run mypy services/common/src/zayd_common/chunking.py services/common/src/zayd_common/document_publishing.py services/api/src/zayd_service_api/app.py --ignore-missing-imports`
- `python3 -m py_compile services/common/src/zayd_common/chunking.py services/common/src/zayd_common/document_publishing.py services/common/tests/test_chunking.py services/common/tests/test_document_publishing.py && git diff --check`

### Acceptance Criteria Result

- Passed. Chunk drafts include immutable `document_version_id`, canonical references, page/section/context metadata, framework version, and per-strategy version. Publishing persists these into `document_chunks` before the atomic retrieval visibility flip.
- Passed. Strategy versions are recorded on chunk rows and in chunk metadata; publishing metadata records the retrieval chunking framework and strategy version set.
- Passed. Tests cover Quran verse, hadith record, fiqh issue, heading section, table, paragraph, and fixed-window overlap boundaries.

### Security and License Review

- No secrets, credentials, production data, restricted religious datasets, PHI, signed URLs, or third-party code were introduced.
- Chunking is deterministic local processing and remains behind existing publishing approval/license gates.

### Known Limitations

- Quran, hadith, and fiqh boundary detection is rule-based and intentionally conservative until richer parser metadata or reviewed structured references are available.

### Follow-up Tasks

- TASK-07-02 Embedding Provider Interface
- TASK-07-03 Full-text Search

### Commit

- Focused commit `feat(retrieval): add versioned chunking framework`
