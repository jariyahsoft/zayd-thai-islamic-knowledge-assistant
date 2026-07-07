# TASK-04-02 — License Registry API

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §15 License Registry
- SRS §23.3 Source License

## Objective

Implement license records covering storage, embedding, commercial use, redistribution, attribution, validity dates and permission evidence.

## Scope

### In Scope

- Implement license records covering storage, embedding, commercial use, redistribution, attribution, validity dates and permission evidence.
- Store permission documents in private object storage.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-04-01

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

- [x] UNKNOWN, PROHIBITED and EXPIRED licenses cannot authorize publication.
- [x] Expiry and replacement of license versions are represented without overwriting history.
- [x] Permission files are access controlled and audited.

## Required Tests

### Unit and Contract Tests

- License CRUD tests
- Expiry tests
- Permission-document access tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/licenses.md`
- `docs/governance/data-licenses.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/licenses.py`
- `services/common/src/zayd_common/__init__.py`
- `services/api/src/zayd_service_api/app.py`
- `services/common/tests/test_licenses.py`
- `services/api/tests/test_licenses_api.py`
- `docs/api/licenses.md`
- `docs/governance/data-licenses.md`
- `tasks/04_data_governance/04-02_license_registry_api.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py`
- `uv run pytest services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py services/common/tests/test_sources.py services/api/tests/test_sources_api.py`
- `uv run ruff check services/common/src/zayd_common/licenses.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py`
- `uv run ruff format --check services/common/src/zayd_common/licenses.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_licenses.py services/api/tests/test_licenses_api.py`
- `uv run mypy services/common/src/zayd_common/licenses.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py`
- `uv run pytest`
- Focused secret-marker scan on changed implementation, docs and task files

### Acceptance Criteria Result

- Passed. `unknown`, `prohibited`, `expired`, and date-expired licenses fail closed for publication authorization.
- Passed. License replacement creates a new `source_licenses` row and preserves the original row for history.
- Passed. Permission document access is RBAC-protected at the API layer, returns metadata only, and writes immutable audit records for success and missing-document denial.

### Security and License Review

- RBAC enforced through existing `licenses.read` and `licenses.manage` dependencies; privileged access inherits existing MFA enforcement.
- Permission evidence is represented by private object keys only; no file contents, signed URLs, production data, restricted datasets, or secrets were added.
- Stable service errors were added for invalid status, invalid permission, invalid date range, missing source/license, missing permission document, and blocked publication.
- Publication checks use deterministic `license-registry-v1` policy logic and fail closed for missing or ambiguous permission states.
- Focused secret-marker scan passed for changed implementation, docs and task-tracking files.

### Known Limitations

- This task stores private object keys and gates metadata access; actual object-storage upload/download and signed URL generation are deferred to storage integration tasks.
- Downstream ingestion, review, publishing and retrieval services must call the registry authorization checks in their respective later tasks.
- No database migration was required because the `source_licenses` table and ORM model already existed from the core schema tasks.

### Follow-up Tasks

- TASK-04-03 — License Policy Engine should centralize and expand deterministic policy decisions for downstream workflows.
- TASK-04-04 — Admin UI should expose source license versions and permission evidence metadata.
- TASK-05-01 and later ingestion/retrieval tasks must enforce source active state and valid license gates before accepting or publishing content.

### Commit

- This task completion commit.
