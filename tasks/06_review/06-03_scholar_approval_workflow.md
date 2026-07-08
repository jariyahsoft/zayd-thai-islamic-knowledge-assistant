# TASK-06-03 — Scholar Approval Workflow

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-REV-008
- FR-REV-010
- FR-REV-011

## Objective

Implement escalation and senior-scholar approval, including optional two-level approval by content risk.

## Scope

### In Scope

- Implement escalation and senior-scholar approval, including optional two-level approval by content risk.
- Enforce separation of duties.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-02

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

- [x] Restricted content cannot publish without required approvals.
- [x] A contributor/reviewer cannot satisfy incompatible approval roles on the same version.
- [x] Approval expiry or revocation is represented explicitly.

## Required Tests

### Unit and Contract Tests

- Approval matrix tests
- Self-approval denial tests
- Two-level approval E2E tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/governance/scholar-approval.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/scholar_approval.py` - Added `ScholarApprovalService` with risk-based approval requirements, active approval creation, expiry, revocation, duplicate active-level protection, role checks, and separation-of-duties checks.
- `services/common/src/zayd_common/database/models.py` - Added `ReviewApproval` model with explicit active/expired/revoked status, validity horizon, revocation actor, reason, and timestamps.
- `database/migrations/0009_scholar_approval_workflow.up.sql` and `database/migrations/0009_scholar_approval_workflow.down.sql` - Added review approval persistence and rollback.
- `services/api/src/zayd_service_api/app.py` - Added approval creation, approval-requirements, and revocation endpoints under the existing review permission boundary.
- `services/common/tests/test_scholar_approval.py` - Added approval matrix, self-approval, incompatible-level, expiry, revocation, and fail-closed requirement tests.
- `services/api/tests/test_document_review_api.py` - Added two-level approval, self-approval denial, and revocation integration tests.
- `docs/governance/scholar-approval.md` - Documented risk matrix, approval roles, expiry/revocation, API surface, audit/privacy, and publishing boundary.
- `database/migrations/README.md` - Registered migration `0009_scholar_approval_workflow`.
- `services/common/src/zayd_common/__init__.py` - Exported scholar approval service types.
- `tasks/06_review/06-03_scholar_approval_workflow.md` - Updated status and completion report.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_scholar_approval.py services/api/tests/test_document_review_api.py -v` - 23 passed.
- `uv run pytest services/common/tests/test_document_review.py services/common/tests/test_scholar_approval.py services/api/tests/test_document_review_api.py services/api/tests/test_review_queue_api.py -v` - 42 passed.
- `uv run ruff check services/common/src/zayd_common/__init__.py services/common/src/zayd_common/scholar_approval.py services/common/tests/test_scholar_approval.py services/common/src/zayd_common/database/models.py services/api/src/zayd_service_api/app.py services/api/tests/test_document_review_api.py` - passed.
- `uv run mypy services/common/src/zayd_common/scholar_approval.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py --ignore-missing-imports` - passed.
- `python3 -m py_compile services/common/src/zayd_common/scholar_approval.py services/common/tests/test_scholar_approval.py services/api/src/zayd_service_api/app.py services/api/tests/test_document_review_api.py && git diff --check` - passed.

### Acceptance Criteria Result

- [x] Restricted content cannot publish without required approvals: `get_requirements` returns required levels `initial`, `scholar`, and `board` for `restricted` risk and reports missing approvals until all required active levels exist.
- [x] A contributor/reviewer cannot satisfy incompatible approval roles on the same version: uploader, task creator, prior approving reviewer, and active prior approver are denied from satisfying incompatible approval levels.
- [x] Approval expiry or revocation is represented explicitly: approvals persist `active`, `expired`, or `revoked`, with `valid_until`, `revoked_at`, `revoked_by`, and `revoke_reason`.

### Security and License Review

- The workflow uses existing `documents.review` RBAC and privileged MFA enforcement in the API layer.
- Senior scholar and board levels enforce role checks; board approval is admin-only in this implementation.
- Approval requirement checks fail closed for unknown document versions and invalid risk values.
- Audit events are sanitized and include approval level, risk, version/task IDs, trace IDs, and policy version without document text or credential data.
- No production data, credentials, restricted religious content, PHI, third-party code, or license-policy changes were introduced.

### Known Limitations

- TASK-06-04 must call approval requirements before changing publish visibility; this task does not publish documents.
- Expiry is service-driven and not yet scheduled as a background job.
- Board approval is mapped to `admin` until a separate board role exists.
- Chunk and citation preview is documented as a publishing boundary; actual preview gating belongs to TASK-06-04/TASK-07.

### Follow-up Tasks

- TASK-06-04 must enforce `ready_for_publish` before freeze/chunk/embed/publish.
- Add a scheduled worker for approval expiry once background jobs are implemented.
- Introduce a dedicated board role if governance requires it.

### Commit

- Focused task commit created for TASK-06-03.
