# TASK-05-01 — Document Upload API

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-ING-001
- FR-ING-003
- FR-ING-005

## Objective

Implement multipart or signed-upload initiation for supported file types.

## Scope

### In Scope

- Implement multipart or signed-upload initiation for supported file types.
- Validate type, size, source and license association; compute SHA-256 and detect duplicates.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-04 complete

## Expected Files

- Implementation files under the relevant `05_ingestion` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Pipeline stages must be idempotent and retryable.
- Preserve original files/text and store derived data separately.
- Use background jobs for expensive processing.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Treat uploaded files and extracted content as untrusted.

## Acceptance Criteria

- [x] Unsupported or oversized files are rejected before processing.
- [x] Duplicate detection returns a safe, actionable result.
- [x] Upload cannot proceed without an eligible source/license combination.

## Required Tests

### Unit and Contract Tests

- File validation tests
- Hash and duplicate tests
- RBAC tests
- Malformed upload tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/document-upload.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/documents.py` - Added document upload registration service, validation, duplicate detection, license/source gating, and audit events
- `services/common/src/zayd_common/__init__.py` - Exported document upload service types
- `services/api/src/zayd_service_api/app.py` - Added `/documents` request/response models, error handling, base64 payload decoding, and upload route
- `services/common/tests/test_documents.py` - Added service-level tests for success, duplicate detection, type/size validation, and license/source rejection
- `services/api/tests/test_documents_api.py` - Added route registration, OpenAPI, RBAC, success, duplicate, and malformed payload coverage
- `docs/api/document-upload.md` - Documented request contract, duplicate behavior, stable errors, and security/audit rules
- `tasks/05_ingestion/05-01_document_upload_api.md` - Updated task status and completion report
- `tasks/00_task_index.md` - Marked TASK-05-01 done and TASK-05-02 ready
- `tasks-update.md` - Recorded task completion and verification evidence

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_documents.py services/api/tests/test_documents_api.py`
- `uv run pytest services/common/tests/test_sources.py services/api/tests/test_sources_api.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py services/common/tests/test_license_policy.py`
- `uv run ruff check services/common/src/zayd_common/documents.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_documents.py services/api/tests/test_documents_api.py`
- `uv run ruff format --check services/common/src/zayd_common/documents.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_documents.py services/api/tests/test_documents_api.py`
- `uv run mypy services/common/src/zayd_common/documents.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py`
- Focused secret-marker scan on changed implementation, docs, and task-tracking files

### Acceptance Criteria Result

- Passed. Unsupported content types, mismatched extensions, malformed payloads, and oversized uploads are rejected before document/version creation.
- Passed. Duplicate content returns a stable `upload_status=\"duplicate\"` response with the existing document/version reference and quarantine key.
- Passed. Upload registration fails closed when the source is missing/inactive, the source license is missing/mismatched, or the deterministic ingestion policy blocks storage.

### Security and License Review

- `POST /documents` requires `documents.upload` and inherits privileged MFA enforcement from the existing RBAC dependency stack.
- Upload bytes are treated as untrusted input; the endpoint validates filename, content type, extension, decoded payload, file size, source state, and license policy before persistence.
- Accepted and duplicate paths emit immutable audit entries with sanitized metadata only: `documents.upload.register` and `documents.upload.duplicate`.
- The implementation stores placeholder quarantine object keys and does not expose signed URLs, raw file contents, or permission-document contents.
- No secrets, production data, restricted religious content, or third-party code were introduced. Focused secret-marker scan passed.

### Known Limitations

- This task registers uploads via JSON `file_base64` payloads rather than multipart or pre-signed object-storage flows; direct object storage integration remains deferred to TASK-05-02.
- Duplicate detection currently scans existing document versions through repository reads; this is acceptable for the current scope but will need indexed lookup optimization as ingestion volume grows.
- Malware scanning, extraction, and downstream review-task creation are not part of this task and remain deferred to later ingestion tasks.

### Follow-up Tasks

- TASK-05-02 — Object Storage Integration should replace placeholder quarantine keys with real upload/storage mechanics.
- TASK-05-03 — Malware Scan Pipeline must validate uploaded files before downstream extraction.
- TASK-05-04 through TASK-05-07 must consume the registered document/version records for parsing, normalization, metadata extraction, and review-task creation.

### Commit

- `feat(ingestion): implement document upload api`
