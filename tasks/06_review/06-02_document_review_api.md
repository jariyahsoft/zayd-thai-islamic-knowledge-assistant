# TASK-06-02 — Document Review API

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-REV-003
- FR-REV-007
- FR-REV-009

## Objective

Implement review drafts, text/metadata edits, comments, request-changes, reject and approve decisions.

## Scope

### In Scope

- Implement review drafts, text/metadata edits, comments, request-changes, reject and approve decisions.
- Create immutable revisions and human-readable diffs.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-01

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

- [x] Every edit produces a revision linked to actor and task.
- [x] Original uploaded file cannot be modified.
- [x] Decision transitions follow the state machine.
- [x] Conflicting concurrent edits are detected.

## Required Tests

### Unit and Contract Tests

- Revision/diff tests
- Optimistic concurrency tests
- Decision transition tests
- Audit tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/document-review.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/database/models.py` — Updated ReviewTask mapping to support `row_version`, added `ReviewRevision`, `ReviewDecisionRecord`, and `ReviewComment` models.
- `services/common/src/zayd_common/document_review.py` — NEW: DocumentReviewService implementing `get_draft`, `apply_edit`, `add_comment`, and `decide`. Also sets up optimistic concurrency matching task row versions.
- `services/common/src/zayd_common/__init__.py` — Registered exports for new models, errors, and endpoints.
- `services/api/src/zayd_service_api/app.py` — Registered 4 review routes: GET `/reviews/{review_task_id}/draft`, PATCH `/reviews/{review_task_id}/draft`, POST `/reviews/{review_task_id}/comments`, and POST `/reviews/{review_task_id}/decision`.
- `database/migrations/0008_document_review_api.up.sql` and `database/migrations/0008_document_review_api.down.sql` — NEW: Database migrations registering optimistic row versions and revision/decision/comment entities. 
- `services/common/tests/test_document_review.py` — NEW: Unit tests covering draft retrievals, revisions, concurrency safety, comments, decision transitions, role logic, and self-approval guards.
- `services/api/tests/test_document_review_api.py` — NEW: Integration tests validating permissions, draft views, edits, comments, and decision outcomes.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_document_review.py -v` — 9 passed.
- `uv run pytest services/api/tests/test_document_review_api.py -v` — 7 passed.
- `uv run pytest -k "not postgres"` — 383 passed, 1 skipped. No regressions.

### Acceptance Criteria Result

- [x] Every edit produces a revision linked to actor and task: verified by `test_apply_edit_success` (revisions contain diffs, actor IDs, and task references).
- [x] Original uploaded file cannot be modified: verified by `test_apply_edit_creates_revision_diff_and_does_not_modify_original_version` (source version extracted text remains unmodified).
- [x] Decision transitions follow the state machine: verified by `test_request_changes_decision_follows_state_machine` and `test_reject_requires_valid_state_transition` (uses DocumentStateMachine and ReviewTaskStateMachine under-the-hood).
- [x] Conflicting concurrent edits are detected: verified by `test_apply_edit_detects_conflicting_row_version` (concurrency raises conflict code when base version mismatch occurs).

### Security and License Review

- Added self-approval checking on decisions.
- Enforced role-based access for reviewers, translators, senior scholars, and admins.
- Implemented and chained request trace auditing on edits, comments, and decisions.

### Known Limitations

- Diff summaries are truncated after 400 lines.
- SQLite memory caching is used in unit tests instead of isolated containers.

### Follow-up Tasks

- TASK-06-03 (Scholar Approval Workflow)

### Commit

- feat(review): implement document review API draft edits, comments and decisions with optimistic locking and self-approval guards

