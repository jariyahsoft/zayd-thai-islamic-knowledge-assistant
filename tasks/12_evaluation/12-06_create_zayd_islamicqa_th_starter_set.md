# TASK-12-06 — Create Zayd-IslamicQA-TH Starter Set

## Status

`TODO`

## Model Tier

Tier S + Human Scholar Review

## Related Requirements

- SRS §17.1 Test Set
- SRS §42 Data Contribution

## Objective

Create reviewed starter cases for taharah, salah, fasting, basic aqidah, unanswerable, high-risk and madhhab-difference topics.

## Scope

### In Scope

- Create reviewed starter cases for taharah, salah, fasting, basic aqidah, unanswerable, high-risk and madhhab-difference topics.
- Separate public and private subsets and provide source/license manifests.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-12-01

## Expected Files

- Implementation files under the relevant `12_evaluation` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Runs must be reproducible and version-aware.
- Separate public and private evaluation material.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect private benchmark cases and reviewer identity.

## Acceptance Criteria

- [ ] Every case has verifiable source, license status and reviewer approval.
- [ ] AI-generated draft answers are not accepted without human review.
- [ ] No restricted text is redistributed beyond its permission.

## Required Tests

### Unit and Contract Tests

- Dataset schema validation
- License manifest checks
- Scholar review sign-off

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `evaluation/datasets/README.md`
- `docs/evaluation/dataset-governance.md`

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
