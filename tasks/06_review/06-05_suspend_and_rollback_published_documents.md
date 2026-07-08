# TASK-06-05 — Suspend and Rollback Published Documents

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-CIT-009
- FR-CIT-010
- FR-ADM-010

## Objective

Allow authorized suspension, archival and rollback to a previously approved version.

## Scope

### In Scope

- Allow authorized suspension, archival and rollback to a previously approved version.
- Flag affected citations and historical answers for re-review.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-04

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

- [x] Suspended content disappears from new retrieval immediately.
- [x] Historical answers show an invalidation warning where applicable.
- [x] Rollback preserves full audit history and does not overwrite versions.

## Required Tests

### Unit and Contract Tests

- Suspension propagation tests
- Rollback E2E test
- Affected-answer discovery tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/content-suspension.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/document_lifecycle.py`
- `services/common/src/zayd_common/database/models.py`
- `services/common/src/zayd_common/rbac.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/tests/test_document_lifecycle.py`
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_document_review_api.py`
- `docs/operations/content-suspension.md`
- `tasks/06_review/06-05_suspend_and_rollback_published_documents.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_document_lifecycle.py -v`
- `uv run pytest services/api/tests/test_document_review_api.py services/common/tests/test_rbac.py -v`
- `uv run ruff check services/common/src/zayd_common/document_lifecycle.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/common/src/zayd_common/rbac.py services/common/tests/test_document_lifecycle.py services/api/src/zayd_service_api/app.py services/api/tests/test_document_review_api.py`
- `uv run mypy services/common/src/zayd_common/document_lifecycle.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/rbac.py services/api/src/zayd_service_api/app.py --ignore-missing-imports`
- `uv run pytest services/common/tests/test_document_lifecycle.py services/common/tests/test_document_publishing.py services/common/tests/test_scholar_approval.py services/common/tests/test_document_review.py services/common/tests/test_rbac.py services/api/tests/test_document_review_api.py services/api/tests/test_review_queue_api.py -v`
- `python3 -m py_compile services/common/src/zayd_common/document_lifecycle.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/common/src/zayd_common/rbac.py services/api/src/zayd_service_api/app.py services/common/tests/test_document_lifecycle.py services/api/tests/test_document_review_api.py && git diff --check`

### Acceptance Criteria Result

- Passed. Suspension and archival set affected published chunks to `is_published=false`; rollback hides the superseded version and restores the selected approved version's chunks.
- Passed. Affected historical answers are discovered from retrieval results and receive `invalidated_at`, `answer_json["invalidation_warning"]`, and a structured warning entry.
- Passed. Rollback points the document to a prior version without overwriting version rows and records an immutable `documents.rollback` audit record.

### Security and License Review

- API routes enforce `documents.archive`; the service also restricts lifecycle changes to `senior_scholar` or `admin` and supports optimistic `base_row_version` checks.
- Lifecycle audit summaries include IDs, status, counts, reasons and policy versions only. They do not include document text, answer bodies, user messages, credentials, signed URLs, production payloads or restricted religious content.
- Senior scholars now receive `documents.archive` so they can execute urgent content safety suspension and rollback while still passing service-side role checks.

### Known Limitations

- Citation and answer invalidation uses local SQLAlchemy models for existing schema tables; full citation registry workflows and answer invalidation UI remain later tasks.
- Rollback requires the target approved version to already have retrieval chunks.

### Follow-up Tasks

- TASK-07-01 — Chunking Framework.
- TASK-08-07 — Citation Registry.
- TASK-11-04 — Answer Invalidation.

### Commit

- Focused commit: `feat(review): add published document lifecycle controls`.
