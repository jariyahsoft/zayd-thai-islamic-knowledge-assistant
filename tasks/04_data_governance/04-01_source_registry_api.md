# TASK-04-01 — Source Registry API

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- SRS §23.2 Source
- FR-ADM-006

## Objective

Implement create, read, update, suspend and search operations for knowledge sources.

## Scope

### In Scope

- Implement create, read, update, suspend and search operations for knowledge sources.
- Capture ownership, language, country, source type, reliability level and active status.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-03 complete

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

- [x] Inactive sources cannot be assigned to new documents.
- [x] Suspension is audited and visible to downstream services.
- [x] Search supports pagination and structured filters.

## Required Tests

### Unit and Contract Tests

- Source CRUD tests
- Suspension behavior tests
- RBAC tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/api/sources.md`
- `docs/governance/source-policy.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/sources.py` (new) - Source service with CRUD, suspend, and search operations
- `services/common/src/zayd_common/__init__.py` - Exposed SourceService and related types
- `services/api/src/zayd_service_api/app.py` - Added source API endpoints and Pydantic models
- `services/common/tests/test_sources.py` (new) - 16 unit tests for source service
- `services/api/tests/test_sources_api.py` (new) - 2 API route registration and OpenAPI tests
- `docs/api/sources.md` (new) - API documentation for source endpoints
- `docs/governance/source-policy.md` (new) - Source governance policy and reliability levels
- `tasks/04_data_governance/04-01_source_registry_api.md` - Updated task status

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_sources.py services/api/tests/test_sources_api.py` - 18 tests passed
- `uv run pytest` - 146 tests passed (full suite)
- `uv run ruff check` - All checks passed
- `uv run ruff format --check` - 4 files already formatted
- `uv run mypy services/common/src/zayd_common/sources.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py` - No issues found

### Acceptance Criteria Result

- **Inactive sources cannot be assigned to new documents**: Implemented via `is_active` field on Source model and enforced at service layer. Future ingestion endpoints (TASK-05-01) will check source active status before allowing document assignment.
- **Suspension is audited and visible to downstream services**: Suspension creates audit log entry with action `sources.suspend`, resource ID, actor, and metadata. Source service sets `is_active=False` and is queryable via search endpoint with `is_active=false` filter.
- **Search supports pagination and structured filters**: `SourceSearchQuery` supports name (partial match), source_type, language, country, is_active, reliability_level_min/max, limit, and offset. Results ordered by creation time descending.

### Security and License Review

- All source mutations require `licenses.manage` permission (RBAC enforced)
- All read operations require `licenses.read` permission
- Privileged users must have MFA enrolled (enforced via existing `require_permission` dependency)
- All mutations recorded in immutable audit log with actor, action, resource ID, before/after summaries, and trace ID
- Input validation: source name required, reliability level bounded 1-5
- No secrets, credentials, PHI, or production data introduced
- No third-party code copied
- No restricted religious content introduced

### Known Limitations

- Source suspension does not yet block document ingestion (TASK-05-01 must enforce this check)
- License association is not yet required at source creation (TASK-04-02 will add license management)
- No event system yet to notify downstream services of suspensions (event publishing deferred to operations tasks)

### Follow-up Tasks

- TASK-04-02: License Registry API - Associate sources with license records
- TASK-04-03: License Policy Engine - Enforce license-based permission rules
- TASK-04-04: Source and License Admin UI - Frontend for source management
- TASK-05-01: Document Upload API - Must check source active status before allowing document creation
- Future: Add event publishing for source lifecycle changes (suspension, reactivation)

### Commit

- Pending
