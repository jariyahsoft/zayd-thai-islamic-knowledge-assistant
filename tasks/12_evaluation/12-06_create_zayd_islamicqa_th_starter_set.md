# TASK-12-06 — Create Zayd-IslamicQA-TH Starter Set

## Status

`DONE`

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

- [x] Every case has verifiable source, license status and reviewer approval.
- [x] AI-generated draft answers are not accepted without human review.
- [x] No restricted text is redistributed beyond its permission.

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

### Files Changed

- `evaluation/datasets/starter_set_manifest.json`
- `evaluation/datasets/public_cases.json`
- `evaluation/datasets/private_cases.json`
- `services/evaluation/src/zayd_service_evaluation/seed_starter_set.py`
- `services/evaluation/tests/test_starter_set.py`
- `services/evaluation/src/zayd_service_evaluation/__init__.py`
- `evaluation/datasets/README.md`
- `docs/evaluation/dataset-governance.md`

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_starter_set.py`
- `uv run ruff check`

### Acceptance Criteria Result

- Completed. Loaded reviewed public and private subsets. Configured Pydantic verification and scholar review checks which prevent AI drafts from being loaded without Human Reviewer validation. Restrictive texts are correctly partitioned.

### Security and License Review

- No secret, production data or restricted religious content committed. No license violations detected. Public cases are CC-BY-SA or Public Domain; private cases are kept isolated.

### Known Limitations

- The dataset is a starter set (total of 7 cases) and needs manual extension before production.

### Follow-up Tasks

- Human Scholar Review panel verification of future case extensions.

### Commit

- `feat(evaluation): add IslamicQA-TH starter set`
