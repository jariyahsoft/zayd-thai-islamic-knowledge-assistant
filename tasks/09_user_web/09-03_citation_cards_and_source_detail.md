# TASK-09-03 — Citation Cards and Source Detail

## Status

`READY`

## Model Tier

Tier A

## Related Requirements

- FR-CIT-005
- FR-CIT-008

## Objective

Create distinct citation cards for Quran, hadith and books plus a source-detail view showing original text, Thai translation, metadata and verification state.

## Scope

### In Scope

- Create distinct citation cards for Quran, hadith and books plus a source-detail view showing original text, Thai translation, metadata and verification state.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-07
- TASK-09-02

## Expected Files

- Implementation files under the relevant `09_user_web` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use generated API clients/contracts where available.
- Meet responsive, accessibility and safe-rendering requirements.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Sanitize rendered content and avoid leaking internal traces.

## Acceptance Criteria

- [ ] AI explanation is visually separated from source text.
- [ ] Invalidated/suspended sources show clear warnings.
- [ ] RTL/LTR content is rendered correctly.

## Required Tests

### Unit and Contract Tests

- Citation component tests
- Source detail E2E
- Accessibility tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/frontend/citations.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Pending

### Commands and Tests Executed

- Pending

### Acceptance Criteria Result

- Pending

### Security and License Review

- Pending

### Known Limitations

- Pending

### Follow-up Tasks

- Pending

### Commit

- Pending
