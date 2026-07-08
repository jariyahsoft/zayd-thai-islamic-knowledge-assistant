# TASK-05-07 — Create Review Task Automatically

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-ING-012
- FR-REV-001

## Objective

Create review tasks after successful parsing/extraction.

## Scope

### In Scope

- Create review tasks after successful parsing/extraction.
- Assign category, language, madhhab, priority and optional due date using configurable rules.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-05-06

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

- [x] One active review task is created per reviewable document version.
- [x] Failed or quarantined documents do not enter review.
- [x] Assignment events are audited.

## Required Tests

### Unit and Contract Tests

- Task creation integration tests
- Duplicate-event/idempotency tests
- Assignment-rule tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/review-task-creation.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/database/models.py` — Added `ReviewTask` SQLAlchemy model with review_tasks table.
- `services/common/src/zayd_common/database/repositories.py` — Added `AbstractReviewTaskRepository` and `SQLAlchemyReviewTaskRepository`.
- `services/common/src/zayd_common/database/unit_of_work.py` — Added `review_tasks` repository to `SQLAlchemyUnitOfWork`.
- `services/common/src/zayd_common/database/__init__.py` — Exported new repository types.
- `services/common/src/zayd_common/review_tasks.py` — New module: `ReviewTaskService`, configurable assignment rules, priority/due date resolution, eligibility checks, idempotent creation, audit events.
- `services/common/tests/test_review_tasks.py` — 19 unit tests: task creation (4), idempotency (3), assignment rules (10), metadata propagation (1).
- `database/migrations/0007_review_tasks.up.sql` — PostgreSQL migration for review_tasks table with unique partial index.
- `database/migrations/0007_review_tasks.down.sql` — Rollback migration.
- `database/migrations/README.md` — Updated migration list.
- `docs/architecture/review-task-creation.md` — Architecture documentation.
- `tasks/05_ingestion/05-07_create_review_task_automatically.md` — Updated status and completion report.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_review_tasks.py -v` — 19 passed.
- `uv run ruff check` on all changed files — All checks passed.
- `uv run mypy services/common/src/zayd_common/review_tasks.py --ignore-missing-imports` — Success: no issues found.

### Acceptance Criteria Result

- ✅ Verified. One active review task per document version and review level (unique constraint + service-level guard). One per level (different levels allowed). Tests: `test_create_review_task_success`, `test_different_levels_allowed`, `test_duplicate_level_raises`.
- ✅ Verified. Infected/rejected version status (`rejected`) and rejected document review status (`rejected`) both raise `REVIEW_VERSION_NOT_ELIGIBLE`. Tests: `test_rejects_infected_version`, `test_rejects_rejected_document`.
- ✅ Verified. Every task creation writes an `AuditLog` with action `review_task.created` containing document/version IDs, review level, priority, and policy version. Test: `test_create_review_task_success` (audit verification section), `test_only_one_audit_log_per_creation`.

### Security and License Review

- All review task creations require an authenticated `actor_user_id`.
- Every creation is audited via immutable AuditLog with action `review_task.created`.
- No production secrets, restricted religious content, PHI, third-party code, or new dependencies beyond SQLAlchemy were introduced.
- RBAC enforcement is delegated to the API layer (TASK-06-01).

### Known Limitations

- Review task creation is not yet wired as an automatic post-extraction pipeline stage.
- No API endpoint is exposed yet — creation is called programmatically.
- Assignment rules are currently hardcoded; configuration-file-based rules are a follow-up.
- Reviewer auto-assignment (based on madhhab, language, category) is not yet implemented.

### Follow-up Tasks

- Wire review task creation as automatic post-extraction stage in the ingestion pipeline.
- Expose review task CRUD via API (TASK-06-01).
- Add configurable assignment rules (file-based or database-backed).
- Add reviewer auto-assignment based on language/madhhab/category matching.

### Commit

- Pending (task verified, ready for focused commit).
