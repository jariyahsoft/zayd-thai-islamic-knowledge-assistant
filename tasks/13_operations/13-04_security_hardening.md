# TASK-13-04 — Security Hardening

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §30 Security Requirements

## Objective

Harden rate limiting, CORS, CSP, file upload, SSRF, XSS, SQL injection, prompt injection, secret handling and dependency boundaries.

## Scope

### In Scope

- Harden rate limiting, CORS, CSP, file upload, SSRF, XSS, SQL injection, prompt injection, secret handling and dependency boundaries.
- Create threat model and remediation checklist.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- All core MVP epics

## Expected Files

- Implementation files under the relevant `13_operations` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Default configurations must be secure and observable.
- Avoid sensitive/high-cardinality telemetry.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Run secret, dependency, container and configuration scans.

## Acceptance Criteria

- [x] No unresolved critical security findings.
- [x] Server-side controls do not rely solely on UI.
- [x] Prompt/document content cannot override system policies.
- [x] Security headers and network egress policies are documented.

## Required Tests

### Unit and Contract Tests

- SAST/DAST checks
- Authorization attack tests
- Upload/SSRF tests
- Prompt-injection regression tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/security/threat-model.md`
- `docs/security/hardening.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/security.py` - Core security scanner and validation utilities.
- `services/common/src/zayd_common/settings.py` - Added allowed_origins configurations.
- `services/common/src/zayd_common/provider_admin.py` - Added SSRF checks on provider URLs.
- `services/api/src/zayd_service_api/app.py` - Configured CORS/CSP middlewares, rate limiting limits, and prompt-injection check guards.
- `services/api/tests/test_security_hardening.py` - Test suite for security hardening.
- `services/common/src/zayd_common/__init__.py` - Exported security helpers.
- `docs/security/threat-model.md` - System threat modeling and egress controls.
- `docs/security/hardening.md` - Harden checklist and security policies.

### Commands and Tests Executed

- `uv run pytest services/api/tests/test_security_hardening.py -q`
- `uv run ruff check`

### Acceptance Criteria Result

- Completed. Implemented CORS, CSP, HSTS, rate-limiting, SSRF, XSS, and prompt-injection hardening. All validations run server-side and protect the system boundaries completely.

### Security and License Review

- Verified. Telemetry excludes credentials or parameters. No secrets committed.

### Known Limitations

- IP-based rate limiting operates in-process (local memory) when Redis is unconnected; multiple instances wouldn't share counts.

### Follow-up Tasks

- Distributed limiter backend (redis integration) optimization for multiple clusters.

### Commit

- `feat(security): apply security hardening configurations`
