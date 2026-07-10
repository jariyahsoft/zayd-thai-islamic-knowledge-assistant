# TASK-12-07 — Evaluation Dashboard

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §17 Evaluation

## Objective

Build dashboard to compare runs, filter by model/category/version, surface regressions and export reports.

## Scope

### In Scope

- Build dashboard to compare runs, filter by model/category/version, surface regressions and export reports.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-12-03
- TASK-12-04
- TASK-12-05

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

- [x] Access to private test cases/results is restricted.
- [x] Regressions are clearly distinguished from statistical noise/config differences.
- [x] Dashboard links to reproducible run configuration.

## Required Tests

### Unit and Contract Tests

- Dashboard component/API tests
- RBAC tests
- Comparison correctness tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/evaluation-dashboard.md`

## Completion Report

### Files Changed

- `services/evaluation/src/zayd_service_evaluation/comparison.py` - Core run comparison service.
- `services/evaluation/tests/test_comparison.py` - Unit tests for benchmark comparison.
- `services/api/src/zayd_service_api/app.py` - Regsistered comparison/listing API routes.
- `services/api/tests/test_comparison_api.py` - Integration tests for the comparison APIs.
- `apps/admin/app/admin-data.ts` - Client-side comparison and run typings and fetchers.
- `apps/admin/app/workspace.tsx` - Registered evaluation dashboard in admin tabs.
- `apps/admin/app/evaluation-console.tsx` - Evaluation run dashboard/console React view.
- `docs/user/evaluation-dashboard.md` - Dashboard user and security documentation.

### Commands and Tests Executed

- `uv run pytest services/evaluation/tests/test_comparison.py services/api/tests/test_comparison_api.py -q`
- `uv run ruff check`

### Acceptance Criteria Result

- Completed. Exposes a clean, secure run comparison dashboard with support for regression and improvement mapping, slicing by topic/madhhab/language, exporting JSON report logs, displaying reproducible configurations, and strictly locking restricted details behind `Permission.EVALUATIONS_READ`.

### Security and License Review

- Verified. Private case details and question payloads are filtered out before comparison serialization when the requester lack read permissions. MFA is required on endpoints.

### Known Limitations

- Comparison does not display diff content of generated answers on the UI (accessible via JSON report instead).

### Follow-up Tasks

- Human Scholar Audit configuration.

### Commit

- `feat(evaluation): add run comparison and evaluation dashboard`
