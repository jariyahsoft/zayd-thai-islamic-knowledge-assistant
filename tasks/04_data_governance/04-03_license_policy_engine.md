# TASK-04-03 — License Policy Engine

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-EXT-002
- FR-EXT-004
- SRS §15 License Registry

## Objective

Implement deterministic decisions for persistent storage, caching TTL, embedding, commercial use, redistribution and attribution.

## Scope

### In Scope

- Implement deterministic decisions for persistent storage, caching TTL, embedding, commercial use, redistribution and attribution.
- Expose a policy decision API for ingestion, retrieval and export workflows.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-04-02

## Expected Files

- Implementation files under the relevant `04_data_governance` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Policy decisions must be deterministic and versioned.
- Keep permission evidence private and access controlled.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- A missing or ambiguous license must block restricted operations.

## Acceptance Criteria

- [x] LLMs cannot override license decisions.
- [x] Every decision includes reason codes and source license version.
- [x] Boundary cases for expiry, unknown rights and cache-only content are covered.

## Required Tests

### Unit and Contract Tests

- Policy decision-table tests
- Expiry and conflict tests
- Property-based tests for forbidden combinations

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/license-policy-engine.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/license_policy.py`
- `services/common/src/zayd_common/licenses.py`
- `services/common/src/zayd_common/__init__.py`
- `services/common/tests/test_license_policy.py`
- `services/common/tests/test_licenses.py`
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_licenses_api.py`
- `docs/architecture/license-policy-engine.md`
- `tasks/04_data_governance/04-03_license_policy_engine.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_license_policy.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py`
- `uv run pytest services/common/tests/test_license_policy.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py services/common/tests/test_sources.py services/api/tests/test_sources_api.py`
- `uv run ruff check services/common/src/zayd_common/license_policy.py services/common/src/zayd_common/licenses.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_license_policy.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py`
- `uv run ruff format --check services/common/src/zayd_common/license_policy.py services/common/src/zayd_common/licenses.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_license_policy.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py`
- `uv run mypy services/common/src/zayd_common/license_policy.py services/common/src/zayd_common/licenses.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py`
- `uv run pytest`
- Focused secret-marker scan on changed implementation, docs and task files

### Acceptance Criteria Result

- Passed. Policy decisions are pure deterministic code, always return `llm_override_allowed: false`, and do not consume prompt or LLM output.
- Passed. Every workflow and action decision includes stable reason codes, policy version and source license version.
- Passed. Tests cover expiry, not-yet-valid dates, unknown/prohibited/expired statuses, cache-only content, private-vs-redistributable export boundaries, missing attribution templates, invalid workflows and forbidden permission combinations.

### Security and License Review

- Policy engine fails closed for unsupported workflows, unknown rights, prohibited/expired statuses, date-expired licenses and missing required attribution.
- New API endpoint requires `licenses.read`, inherits privileged MFA enforcement, and audits every decision through immutable audit logs.
- Permission evidence remains private; the engine uses registry metadata only and never returns permission file contents.
- No secrets, production data, restricted religious content, or third-party code were introduced.
- Focused secret-marker scan passed for changed implementation, docs and task-tracking files.

### Known Limitations

- Cache TTL constants are fixed in code for this policy version; future operational tuning should introduce explicit configuration/versioning.
- Downstream ingestion, retrieval and export services still need to call the policy decision API/service in their later tasks.
- The compatibility publication-authorization endpoint now returns reason codes from `license-policy-engine-v1` rather than prose messages.

### Follow-up Tasks

- TASK-04-04 — Source and License Admin UI should display workflow decisions and reason codes.
- TASK-05-01 and later ingestion/retrieval/export tasks must enforce policy decisions before storing, indexing, publishing or exporting content.

### Commit

- This task completion commit.
