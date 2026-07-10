# TASK-10-02 — Document Review Workspace

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-REV-003
- FR-REV-007

## Objective

Build side-by-side original document, extracted text, metadata, translation, chunk preview, comments and diff workspace.

## Scope

### In Scope

- Build side-by-side original document, extracted text, metadata, translation, chunk preview, comments and diff workspace.
- Support autosaved drafts and explicit decisions.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-02
- TASK-10-01

## Expected Files

- Implementation files under the relevant `10_admin_reviewer` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Server-side RBAC is authoritative.
- Protect sensitive source, reviewer and operational information.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Use least privilege for reviewer/admin data.

## Acceptance Criteria

- [x] Unsaved changes are protected.
- [x] Concurrent edits are surfaced.
- [x] Original source file is read-only.
- [x] All decisions and edits are auditable.

## Required Tests

### Unit and Contract Tests

- Review workspace E2E
- Autosave/recovery tests
- Concurrency conflict tests
- Accessibility tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/document-review.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `apps/reviewer/app/reviews/[reviewTaskId]/page.tsx` — added route entry for the document review workspace.
- `apps/reviewer/app/reviews/[reviewTaskId]/workspace.tsx` — added the reviewer workspace UI with read-only source pane, editable extracted text, metadata JSON editor, chunk preview, comments, diff, autosave/save, decision submission, dirty-state unload guard, and conflict messaging.
- `apps/reviewer/app/reviews/[reviewTaskId]/workspace.test.ts` — added source-level UI checks for unsaved-change protection, conflict surfacing, required workspace panels, and responsive styling hooks.
- `apps/reviewer/app/reviewer-data.ts` — added typed document review API helpers for draft fetch, draft update, comment creation, and decision submission.
- `apps/reviewer/app/globals.css` — added responsive workspace layout and control styling.
- `docs/user/document-review.md` — documented reviewer workflow, RBAC boundary, unsaved-change behavior, concurrency handling, read-only source boundary, audit behavior, and current limitations.
- `services/common/src/zayd_common/document_review.py` — kept behavior unchanged while fixing focused lint/type issues found during verification.
- `services/common/tests/test_document_review.py` — kept behavior unchanged while fixing focused lint issues found during verification.
- `tasks/00_task_index.md` — task board status updated for TASK-10-02 and TASK-10-03 readiness.
- `tasks-update.md` — recorded implementation, verification, review notes, and residual risks.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_document_review.py services/api/tests/test_document_review_api.py services/common/tests/test_reviewer_dashboard.py services/api/tests/test_review_queue_api.py -q` — 42 passed.
- `uv run ruff check services/common/src/zayd_common/document_review.py services/common/tests/test_document_review.py services/api/src/zayd_service_api/app.py services/api/tests/test_document_review_api.py services/common/src/zayd_common/review_queue.py services/common/tests/test_reviewer_dashboard.py services/api/tests/test_review_queue_api.py` — passed after focused formatting/line-length fixes.
- `uv run mypy services/common/src/zayd_common/document_review.py services/api/src/zayd_service_api/app.py services/common/src/zayd_common/review_queue.py` — passed.
- `git diff --check` — passed.
- Frontend `@zayd/reviewer` test/typecheck/build commands were not executable in this environment because `node`, `pnpm`, and `corepack` are unavailable.

### Acceptance Criteria Result

- Passed for implementation. Unsaved text/metadata edits set dirty state, activate a browser unload guard, and are autosaved after a short delay or saved explicitly.
- Passed. The workspace sends `base_task_row_version` for edits and decisions and surfaces `DOCUMENT_REVIEW_CONFLICT` with a reload prompt.
- Passed. The original source pane uses the initially loaded draft text and source file key as read-only display; edits go through review revisions.
- Passed. Edits, comments, and decisions continue to use TASK-06-02 APIs, which write revision/comment/decision audit records; regression tests pass.

### Security and License Review

- No secrets, production data, restricted religious content, third-party code, or license-impacting assets were introduced.
- The UI relies on existing server-side `documents.review`, assignment, scholar-level, self-approval, and optimistic-locking enforcement.
- The original file key is displayed as metadata only; no signed URL or mutable source-file operation was added.
- The workspace renders text through React text/textarea/pre elements and does not use unsafe HTML.

### Known Limitations

- Node-based reviewer app test/typecheck/build verification still needs to run in a Node-enabled environment.
- The source pane displays object-key metadata and read-only extracted text; inline signed original-file preview is deferred.
- Chunk preview is local and read-only, derived from current editor text; it is not a publishing chunk plan.
- Autosave is client-timer based and still depends on the same optimistic-lock API as explicit save.

### Follow-up Tasks

- TASK-10-03 — Scholar Approval Workspace
- Future storage/file-preview work can add signed read-only source preview without changing the review edit API.

### Commit

- Pending
