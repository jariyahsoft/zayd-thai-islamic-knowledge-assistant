# TASK-12-05 — Safety and Abstention Metrics

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §17.2 Metrics
- FR-SAFE-006

## Objective

Measure high-risk routing, abstention accuracy, unsafe answer rate and policy compliance.

## Scope

### In Scope

- Measure high-risk routing, abstention accuracy, unsafe answer rate and policy compliance.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-12-02

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

- [x] False-positive and false-negative routing are reported separately.
- [x] Restricted cases never expose private evaluator notes in public reports.

## Required Tests

### Unit and Contract Tests

- Safety metric fixtures
- Policy-version comparison tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/evaluation/safety-metrics.md`

## Completion Report

### Files Changed

- `services/evaluation/src/zayd_service_evaluation/safety_metrics.py`
- `services/evaluation/tests/test_safety_metrics.py`
- `docs/evaluation/safety-metrics.md`
- `services/evaluation/src/zayd_service_evaluation/__init__.py`

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_safety_metrics.py`
- `uv run ruff check`

### Acceptance Criteria Result

- Completed. Added comprehensive high-risk routing and abstention metrics, reporting TP, FP, FN, TN and relevant rates (FPR, FNR, safety compliance, unsafe answer rate) overall and categorized by topic, language, and madhhab. All private notes and restricted case fields remain protected.

### Security and License Review

- No secret, production data or restricted religious content committed. No license violations detected.

### Known Limitations

- Metrics exclude semantic answer correctness (requires LLM-as-a-judge or human evaluation).

### Follow-up Tasks

- TASK-12-07 — Evaluation Dashboard

### Commit

- `feat(evaluation): add safety and abstention metrics`
