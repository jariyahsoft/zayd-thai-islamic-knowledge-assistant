# TASK-06-04 — Document Publishing Service

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-ING-013
- FR-RET-009
- FR-CIT-002

## Objective

Freeze the approved document version, generate chunks, embeddings and canonical citations, then atomically expose it for retrieval.

## Scope

### In Scope

- Freeze the approved document version, generate chunks, embeddings and canonical citations, then atomically expose it for retrieval.
- Implement idempotent retry and compensation for partial failures.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-03

## Expected Files

- Implementation files under the relevant `06_review` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use optimistic locking or equivalent concurrency control.
- Persist every decision and revision before changing publish visibility.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Prevent self-approval and unauthorized publication.

## Acceptance Criteria

- [x] No half-published document is searchable.
- [x] Published version and pipeline versions are recorded.
- [x] Retry does not duplicate chunks, embeddings or citations.
- [x] License policy is rechecked immediately before publish.

## Required Tests

### Unit and Contract Tests

- Publish transaction tests
- Worker retry/idempotency tests
- License-change race test
- Retrieval visibility test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/publishing-pipeline.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/document_publishing.py`
- `services/common/src/zayd_common/database/models.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/tests/test_document_publishing.py`
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_document_review_api.py`
- `docs/architecture/publishing-pipeline.md`
- `tasks/06_review/06-04_document_publishing_service.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_document_publishing.py services/api/tests/test_document_review_api.py -v`
- `uv run ruff check services/common/src/zayd_common/document_publishing.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/common/tests/test_document_publishing.py services/api/src/zayd_service_api/app.py services/api/tests/test_document_review_api.py`
- `uv run mypy services/common/src/zayd_common/document_publishing.py services/common/src/zayd_common/database/models.py services/api/src/zayd_service_api/app.py --ignore-missing-imports`
- `uv run pytest services/common/tests/test_document_publishing.py services/common/tests/test_scholar_approval.py services/common/tests/test_document_review.py services/api/tests/test_document_review_api.py services/api/tests/test_review_queue_api.py -v`
- `python3 -m py_compile services/common/src/zayd_common/document_publishing.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_document_publishing.py services/api/tests/test_document_review_api.py && git diff --check`

### Acceptance Criteria Result

- Passed. Publishing uses one database transaction and keeps chunks unpublished until final visibility flip.
- Passed. `document_versions.metadata_json["publishing"]`, response fields, audit records and chunk metadata record publish, license, approval, chunking, embedding and citation pipeline versions.
- Passed. Repeated publish calls for the same already published version return the existing chunk set with `idempotent=true`; partially generated unpublished chunks are replaced before publish.
- Passed. The service evaluates `evaluate_license_policy(..., workflow="retrieval")` inside the publish transaction immediately before chunk generation and visibility changes.

### Security and License Review

- RBAC enforces `documents.publish` at the API layer and service-side role checks restrict publishing to `senior_scholar` or `admin`.
- Publish fails closed for missing approvals, expired approvals, invalid status, missing license, denied retrieval license policy and empty content.
- Audit summaries are sanitized and include only IDs, status, counts, policy versions and reason codes. No document text, secrets, production data, signed URLs or restricted datasets were introduced.

### Known Limitations

- Embedding and canonical citation provider integrations are recorded as deterministic pipeline metadata on chunks; provider-backed embedding records and citation registry rows remain later retrieval/orchestrator tasks.
- Chunking is a conservative local paragraph/word-count strategy for the publish gate; TASK-07-01 will provide the dedicated retrieval chunking framework.

### Follow-up Tasks

- TASK-06-05 — Suspend and Rollback Published Documents.
- TASK-07-01 — Chunking Framework.
- TASK-08-07 — Citation Registry.

### Commit

- Focused commit: `feat(review): add document publishing service`.
