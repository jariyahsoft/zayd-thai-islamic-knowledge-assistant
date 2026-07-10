# TASK-11-05 — Convert Incident to Regression Test

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-FDB-007
- SRS §36 Testing

## Objective

Allow authorized reviewers to create sanitized evaluation cases from confirmed incidents.

## Scope

### In Scope

- Allow authorized reviewers to create sanitized evaluation cases from confirmed incidents.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-11-03
- EPIC-12

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

- [ ] Personal data is redacted before test creation.
- [ ] Expected behavior and source references are required.
- [ ] Created case retains incident provenance without exposing restricted details.

## Required Tests

### Unit and Contract Tests

- Redaction tests
- Evaluation-case creation E2E
- Permission tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/evaluation/incident-regressions.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/evaluation/src/zayd_service_evaluation/incident_regressions.py`
- `services/evaluation/src/zayd_service_evaluation/__init__.py`
- `services/api/src/zayd_service_api/app.py`
- `services/evaluation/tests/test_incident_regressions.py`
- `services/api/tests/test_incident_regressions_api.py`
- `docs/evaluation/incident-regressions.md`
- Task status and execution records.

### Commands and Tests Executed

- `uv run pytest -q services/evaluation/tests/test_incident_regressions.py services/evaluation/tests/test_evaluation_schema.py services/common/tests/test_incident_management.py services/api/tests/test_incident_regressions_api.py` — 13 passed.
- Focused Ruff check and format check — passed.
- Focused MyPy — passed.
- `git diff --check` — passed.

### Acceptance Criteria Result

- Passed. Authorized users with both feedback and evaluation management permissions can create
  private draft candidates from resolved/closed incidents. Deterministic redaction covers emails,
  Thai phone numbers, and Thai national ID patterns before persistence; expected behavior and source
  references remain required by the evaluation contract; bounded incident provenance and audit/timeline
  records exclude incident/reporter/conversation payloads.

### Security and License Review

- The route is protected by existing privileged MFA/RBAC enforcement and requires both
  `feedback.manage` and `evaluations.manage` at service level. Incident summaries and linked content
  are never copied. Candidates are forced to private/draft; human scholar/QA approval remains required
  before use as reviewed benchmark content.

### Known Limitations

- Pattern redaction cannot identify all contextual personal or restricted information; reviewers must
  inspect candidates before approval. This task creates candidates only and does not approve religious
  expected behavior or publish a benchmark case.

### Follow-up Tasks

- TASK-13-08 is now dependency-ready. Human scholar/QA review is required before a candidate becomes
  approved benchmark content.

### Commit

- Focused task commit created; see Git history for the commit identifier.
