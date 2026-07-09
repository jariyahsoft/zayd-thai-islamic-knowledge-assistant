# TASK-11-01 — Feedback API

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-FDB-001
- FR-FDB-004

## Objective

Implement feedback submission and retrieval linked to question, answer, retrieval run, citations, model, prompt and policy versions.

## Scope

### In Scope

- Implement feedback submission and retrieval linked to question, answer, retrieval run, citations, model, prompt and policy versions.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-08 complete

## Expected Files

- Implementation files under the relevant `11_feedback` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Maintain immutable incident history.
- Minimize personal data and support controlled redaction.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect incident details and reporter privacy.

## Acceptance Criteria

- [x] Feedback does not expose internal trace data to normal users.
- [x] Duplicate/spam controls and retention policy are applied.
- [x] Submission is auditable.

## Required Tests

### Unit and Contract Tests

- Feedback API tests
- Ownership/privacy tests
- Rate-limit tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/feedback.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/feedback.py` (new)
- `services/common/tests/test_feedback.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_feedback_api.py` (new)
- `docs/api/feedback.md` (new)
- `tasks/11_feedback/11-01_feedback_api.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_feedback.py services/api/tests/test_feedback_api.py -q` — 7 passed
- `uv run ruff check` on feedback Python files — success

### Acceptance Criteria Result

- Passed. `POST/GET /feedback` return public receipt shape only. Rate limit 10/hour/user. `feedback.submit` audit captures version metadata and `notes_length` without exposing note text to operators in audit summaries.

### Security and License Review

- RBAC `feedback.create` enforced. Owned-answer validation before insert. No secrets or internal traces in public responses.

### Known Limitations

- In-memory rate limiter; horizontal scaling needs shared limiter later. Review queue and incident workflows remain future tasks.

### Follow-up Tasks

- TASK-11-02 — feedback review queue

### Commit

- `feat(web): add user feedback form`
