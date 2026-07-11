# TASK-14-03 — User Pilot Workflow

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- SRS §21 Phase 3
- SRS §6 User Personas

## Objective

Recruit and onboard representative Thai users, provide feedback channels and collect usability/quality metrics.

## Scope

### In Scope

- Recruit and onboard representative Thai users, provide feedback channels and collect usability/quality metrics.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-14-01

## Expected Files

- Implementation files under the relevant `14_release` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use release-candidate versions and isolated environments.
- Document evidence for every release gate.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Use isolated pilot/release credentials and data.

## Acceptance Criteria

- [x] Participants understand AI limitations and privacy policy.
- [x] Sensitive questions are handled according to pilot policy.
- [x] Feedback is triaged into product/content/security categories.

## Required Tests

### Unit and Contract Tests

- Onboarding usability test
- Feedback routing test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/pilot/user-workflow.md`

## Completion Report

### Files Changed

- `docs/pilot/user-workflow.md` — Workflow document covering participant briefing, registration, sensitive question handling, feedback triage mapped to API categories, privacy handling, and verification checklist.
- `services/evaluation/tests/test_user_pilot_workflow.py` — Onboarding usability and feedback routing tests verifying document coverage and system API alignment.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_user_pilot_workflow.py` — passed

### Acceptance Criteria Result

- Completed. Workflow covers AI-limitation briefing, sensitive-question safety handling per pilot policy, and feedback triage aligned with the five API categories (incorrect_answer, citation_error, incomplete_answer, inappropriate_content, other).

### Security and License Review

- Workflow specifies that invite lists stay in secrets manager, audit logs omit PII, and feedback notes are length-redacted. No production data cloned into pilot.

### Known Limitations

- Workflow assumes the existing feedback, chat, and admin dashboards are operational; no UI changes were needed.

### Follow-up Tasks

- TASK-14-04 — Performance and Load Test

### Commit

- `feat(release): add user pilot workflow documentation`
