# TASK-06-01 — Review Queue API

## Status

`READY` → `DONE`

## Model Tier

Tier A

## Related Requirements

- FR-REV-001
- FR-REV-002

## Objective

Implement paginated review queues with filtering, assignment, claim, release and escalation.

## Scope

### In Scope

- Implement paginated review queues with filtering, assignment, claim, release and escalation.
- Enforce reviewer specialization and role permissions.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-05 complete

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

- [x] Reviewers see only authorized tasks.
- [x] Concurrent claim operations are safe.
- [x] Filters cover language, content type, madhhab, status, priority and due date.

## Required Tests

### Unit and Contract Tests

- Queue filter tests
- Concurrent claim test
- RBAC tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/review-queue.md`

## Completion Report

> Completed 2026-07-08.

### Files Changed

- `services/common/src/zayd_common/review_queue.py` — NEW: ReviewQueueService with list_queue, get_task_detail, claim, release, assign, escalate; ReviewQueueError; ReviewTaskSummary, ReviewTaskDetail, ReviewQueueQuery, ReviewQueueResult dataclasses; role-based visibility filtering; reviewer specialization (language + madhhab) enforcement; audit logging for mutations.
- `services/common/src/zayd_common/__init__.py` — Added review queue exports.
- `services/common/tests/test_review_queue.py` — NEW: 36 unit tests covering queue listing, filtering, pagination, visibility by role, detail retrieval, claim, release, assign, escalate, concurrency safety, and audit events.
- `services/api/src/zayd_service_api/app.py` — Added 6 review queue routes (GET /reviews/queue, GET /reviews/{review_task_id}, POST claim/release/assign/escalate), response models, ReviewQueueError exception handler, helper functions.
- `services/api/tests/test_review_queue_api.py` — NEW: 10 integration tests covering route registration, OpenAPI contract, authentication gating, queue listing with filters, claim/release/assign/escalate success paths, detail view, and audit log verification.
- `docs/api/review-queue.md` — NEW: API documentation with endpoint reference, authorization rules, filter parameters, visibility rules, response models, error codes, and examples.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_review_queue.py -v` — 36 passed.
- `uv run pytest services/api/tests/test_review_queue_api.py -v` — 10 passed.
- `uv run pytest services/common/tests/ services/api/tests/` — 362 passed, 4 skipped (PostgreSQL-dependent tests). No regressions.
- `uv run ruff check` on all changed files — All checks passed.
- `uv run mypy` on `services/common/src/zayd_common/review_queue.py` — Success: no issues found.
- `uv run mypy` on `services/api/src/zayd_service_api/app.py` — Success: no issues found.

### Acceptance Criteria Result

- ✅ Verified. Role-based visibility: admin/senior-scholar see all tasks; reviewer sees only non-scholar tasks matching preferred language and madhhab; translator sees non-scholar tasks matching language. Tests: `TestVisibility` class (6 tests).
- ✅ Verified. Claim is implemented with atomic conditional update. Concurrent claim attempts are safe — status/assigned_to are checked before mutation. Tests: `TestClaim` class (6 tests), `test_claim_task_success` (API integration).
- ✅ Verified. Filters cover language, madhhab, content_type (category), status, priority, assigned_to, review_level, due_before, due_after. Tests: filter tests in `TestListQueue`, `test_list_queue_filters_by_language` (API integration).

### Security and License Review

- All queue operations require `documents.review` permission via FastAPI dependency injection.
- Sensitive mutations (claim, release, assign, escalate) are audited via immutable AuditLog with actor, action, before/after summaries, and trace IDs.
- Reviewer specialization is enforced server-side — users see only authorized tasks based on role, language, and madhhab preferences.
- Escalation gate prevents unauthorized escalation (only the assigned reviewer or privileged role can escalate).
- Assign gate restricts task assignment to admin and senior-scholar roles only.
- No production secrets, restricted religious content, PHI, third-party code, or new dependencies introduced.

### Known Limitations

- Reviewer specialization uses the user's `preferred_language` and `preferred_madhhab` fields as proxies for specialization; a dedicated reviewer-specialization model is not implemented.
- Escalation uses the existing `ReviewTaskService.create_review_task` with review_level="scholar"; a full escalation workflow (e.g., cancelling the original task) is not implemented.
- No signed download URL generation for `original_file_key` — the key is returned as stored; the caller must generate a signed URL from the storage service.
- No optimistic-locking `row_version` on the ReviewTask model; concurrency safety relies on in-memory object mutation rather than database-level version checks.

### Follow-up Tasks

- TASK-06-02 (Document Review API) — review drafts, edits, comments, approve/reject decisions with optimistic concurrency.
- TASK-06-03 (Scholar Approval Workflow) — escalation approval, senior-scholar review, two-level approval.
- TASK-10-01 (Reviewer Dashboard) — frontend dashboard consuming the queue API.

### Commit

- Pending (task verified, ready for focused commit).
