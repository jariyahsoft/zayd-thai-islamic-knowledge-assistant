# TASK-10-01 — Reviewer Dashboard

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-REV-001
- FR-REV-002

## Objective

Build reviewer dashboard showing pending, assigned, overdue, changes-requested and feedback work.

## Scope

### In Scope

- Build reviewer dashboard showing pending, assigned, overdue, changes-requested and feedback work.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-06 complete

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

- [x] Counts match authorized queue data.
- [x] Filters and pagination work on mobile/desktop reviewer layouts.
- [x] No unauthorized content metadata leaks.

## Required Tests

### Unit and Contract Tests

- Dashboard component tests
- RBAC E2E tests
- Queue count consistency tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/reviewer-dashboard.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `apps/reviewer/app/layout.tsx` — switched reviewer app metadata/lang to the dashboard experience and loaded reviewer-specific global styles.
- `apps/reviewer/app/page.tsx` — replaced placeholder shell with the reviewer dashboard page.
- `apps/reviewer/app/globals.css` — added responsive dashboard styling for summary cards, filters, queue cards, badges, and feedback triage blocks.
- `apps/reviewer/app/reviewer-dashboard.tsx` — added dashboard UI with summary counters, filter tabs, status filter, queue preview, feedback triage panel, and auth-aware loading/error handling.
- `apps/reviewer/app/reviewer-data.ts` — added typed API client helpers for `/auth/me` and `/reviews/dashboard`.
- `apps/reviewer/app/reviewer-dashboard.test.ts` — added component/source-level checks for dashboard rendering and responsive styling hooks.
- `apps/reviewer/app/smoke.test.ts` — updated smoke coverage to assert the page exports the reviewer dashboard.
- `services/common/src/zayd_common/review_queue.py` — added reviewer dashboard summary/result models, dashboard aggregation, reusable queue pagination/filter helpers, and RBAC-safe feedback visibility gating.
- `services/common/src/zayd_common/__init__.py` — exported the new reviewer dashboard types.
- `services/common/tests/test_reviewer_dashboard.py` — added dashboard count coverage plus a permission test proving non-feedback roles receive no feedback data.
- `services/api/src/zayd_service_api/app.py` — added `/reviews/dashboard` response models, serialization helpers, and endpoint wiring.
- `services/api/tests/test_review_queue_api.py` — added integration coverage for dashboard counts and the feedback visibility boundary.
- `docs/user/reviewer-dashboard.md` — documented dashboard purpose, filters, RBAC behavior, and privacy boundaries.
- `tasks/00_task_index.md` — task board status updated for TASK-10-01 and TASK-10-02 readiness.
- `tasks-update.md` — recorded implementation, verification, review notes, and residual risks.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_reviewer_dashboard.py services/api/tests/test_review_queue_api.py -q`
- `uv run ruff check services/common/src/zayd_common/review_queue.py services/common/tests/test_reviewer_dashboard.py services/api/src/zayd_service_api/app.py services/api/tests/test_review_queue_api.py`
- `uv run mypy services/common/src/zayd_common/review_queue.py services/api/src/zayd_service_api/app.py`
- `git diff --check`
- Frontend `@zayd/reviewer` test/typecheck/build commands were not executable in this environment because `node`, `pnpm`, and `corepack` are unavailable.

### Acceptance Criteria Result

- Passed. Dashboard summary counters are derived from the same authorized queue view used for task listings, and tests verify visible counts plus reviewer-scoped assigned/overdue/changes-requested values.
- Passed for implementation; partial verification only in this environment. The reviewer app includes responsive mobile-safe filters, summary cards, and queue/feedback panels, and source-level UI tests were added, but Node-based execution remains blocked by missing local tooling.
- Passed. Feedback summary data is now gated by `feedback.read`, so roles with `documents.review` but without feedback visibility do not receive feedback counts or items.

### Security and License Review

- No secrets, production data, restricted religious content, or third-party code were introduced.
- `/reviews/dashboard` requires `documents.review`, while feedback triage data inside the response is additionally filtered by effective `feedback.read` permission.
- The dashboard returns only compact triage metadata and omits full feedback notes and document content.
- No new license or provenance impact was introduced.

### Known Limitations

- The dashboard links to `/reviews/queue`, `/reviews/{id}`, and `/feedback`, but the dedicated workspace screens remain follow-up tasks.
- Queue pagination is currently preview-oriented and capped for dashboard use rather than infinite scrolling.
- Feedback triage is summary-only until TASK-11-02 provides the dedicated feedback review queue UI.
- Reviewer frontend runtime/build verification is still required in a Node-enabled environment.

### Follow-up Tasks

- TASK-10-02 — Document Review Workspace
- TASK-11-02 — Feedback Review Queue

### Commit

- Pending
