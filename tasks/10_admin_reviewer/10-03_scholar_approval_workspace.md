# TASK-10-03 — Scholar Approval Workspace

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-REV-008
- FR-REV-011

## Objective

Create senior-scholar view of review history, source/license status, conflicts, madhhab metadata and approval actions.

## Scope

### In Scope

- Create senior-scholar view of review history, source/license status, conflicts, madhhab metadata and approval actions.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-03
- TASK-10-02

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

- [x] Required evidence and license information is visible before approval.
- [x] Self-approval restrictions are enforced server-side and reflected in UI.

## Required Tests

### Unit and Contract Tests

- Scholar approval E2E
- Separation-of-duties tests
- License-block UI tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/scholar-approval.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `apps/reviewer/app/approvals/[reviewTaskId]/page.tsx` — added route entry for the scholar approval workspace.
- `apps/reviewer/app/approvals/[reviewTaskId]/workspace.tsx` — added the senior-scholar workspace with evidence preview, source/license visibility, madhhab/conflict metadata, approval matrix, approval creation, revocation, and history panels.
- `apps/reviewer/app/approvals/[reviewTaskId]/workspace.test.ts` — added source-level UI checks for evidence/license sections, self-approval denial messaging, revoke flow hooks, and responsive styling hooks.
- `apps/reviewer/app/reviewer-data.ts` — extended typed reviewer client support for approval requirements/history, approval create/revoke, public source detail, admin license detail, and license policy decision endpoints; also added scholar-workspace draft metadata fields.
- `apps/reviewer/app/globals.css` — added responsive scholar approval workspace styling.
- `apps/reviewer/app/smoke.test.ts` — extended route smoke coverage for the scholar approval page.
- `services/common/src/zayd_common/document_review.py` — enriched review drafts with document/source/license identity fields plus revision history required by the scholar workspace.
- `services/common/src/zayd_common/scholar_approval.py` — added approval-history listing for one document version.
- `services/api/src/zayd_service_api/app.py` — extended review draft response payload and added `GET /documents/{document_version_id}/approvals`.
- `services/api/tests/test_document_review_api.py` — added contract coverage for enriched review drafts, approval-history endpoint, and updated OpenAPI assertions.
- `docs/user/scholar-approval.md` — documented scholar approval workflow, access boundaries, evidence/license visibility, and current limitations.
- `tasks/00_task_index.md` — updated TASK-10-03 to `DONE`.
- `tasks-update.md` — recorded implementation, verification, review notes, residual risks, and notification status.

### Commands and Tests Executed

- `uv run pytest services/api/tests/test_document_review_api.py -q` — 19 passed.
- `uv run ruff check services/common/src/zayd_common/document_review.py services/common/src/zayd_common/scholar_approval.py services/api/src/zayd_service_api/app.py services/api/tests/test_document_review_api.py` — passed.
- `uv run mypy services/common/src/zayd_common/document_review.py services/common/src/zayd_common/scholar_approval.py services/api/src/zayd_service_api/app.py --ignore-missing-imports` — passed.
- `git diff --check` — passed.
- Frontend `@zayd/reviewer` test/typecheck/build commands were not executable in this environment because `node`, `pnpm`, and `corepack` are unavailable.

### Acceptance Criteria Result

- [x] Required evidence and license information is visible before approval. The workspace now loads review draft identity fields, source detail, admin license detail, license policy decision, revision summary, and approval history before approval actions are shown.
- [x] Self-approval restrictions are enforced server-side and reflected in UI. Approval creation continues to depend on TASK-06-03 service-side checks, and the workspace surfaces `SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED` as explicit user feedback.

### Security and License Review

- No secrets, production data, restricted religious content, or third-party code were introduced.
- Server-side RBAC and MFA remain authoritative. The workspace consumes existing protected APIs and does not attempt client-side authorization bypasses.
- License visibility uses existing `licenses.read`-protected admin endpoints already granted to `reviewer`, `senior_scholar`, and `admin` roles in repository RBAC.
- The UI exposes metadata, policy reason codes, and approval history only; it does not reveal signed URLs, raw object contents beyond review text, provider secrets, or internal traces.

### Known Limitations

- Reviewer frontend runtime/build verification still needs a Node-enabled environment.
- The scholar workspace composes several existing APIs rather than using a dedicated aggregate endpoint, so it issues multiple requests per load.
- Approval history currently reflects approval records only; review comments and revision summaries remain read-only draft data rather than a unified timeline component.

### Follow-up Tasks

- Future reviewer-app work can consolidate source/license/approval data behind a dedicated scholar aggregate endpoint if request volume becomes a concern.
- TASK-06-04/TASK-06-05 continue to own publish/suspend/archive lifecycle enforcement after approvals are complete.

### Commit

- Pending
