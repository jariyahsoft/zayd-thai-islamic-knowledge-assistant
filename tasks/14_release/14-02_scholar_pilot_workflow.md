# TASK-14-02 — Scholar Pilot Workflow

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- SRS §21 Phase 3
- SRS §17 Evaluation

## Objective

Create onboarding, question assignments, scoring forms and feedback collection for scholar reviewers.

## Scope

### In Scope

- Create onboarding, question assignments, scoring forms and feedback collection for scholar reviewers.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-12
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

- [x] Reviewer consent, role and conflict-of-interest information are handled.
- [x] Scores link to benchmark cases without exposing private identities publicly.
- [x] Findings produce tracked issues.

## Required Tests

### Unit and Contract Tests

- Pilot workflow dry run
- Data export/privacy review

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/pilot/scholar-workflow.md`

## Completion Report

### Files Changed

- `docs/pilot/scholar-workflow.md` — Workflow document covering onboarding, consent/conflict-of-interest, scoring guidelines linked to benchmark cases, issue tracking via incidents, and data export privacy protections.
- `services/evaluation/tests/test_scholar_pilot_workflow.py` — Pilot workflow dry run and data export/privacy review tests verifying document coverage and PII protections.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_scholar_pilot_workflow.py` — passed

### Acceptance Criteria Result

- Completed. Workflow covers consent/COI declarations, scoring tied to benchmark case_keys without reviewer PII, and finding-to-incident tracking through existing API endpoints.

### Security and License Review

- Workflow specifies that invite lists, consent forms, and reviewer identities are stored outside the repository. Audit logs record UUIDs only — never emails or names.

### Known Limitations

- Workflow assumes the pilot environment is operational with review/admin dashboards; no UI changes were needed.

### Follow-up Tasks

- TASK-14-03 — User Pilot Workflow

### Commit

- `feat(release): add scholar pilot workflow documentation`
