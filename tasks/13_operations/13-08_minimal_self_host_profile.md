# TASK-13-08 — Minimal Self-host Profile

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- FR-OSS-001
- FR-OSS-010
- SRS §43.1 Minimal

## Objective

Create a minimal Docker Compose profile with web, API, worker, PostgreSQL/pgvector, Redis, MinIO and local/cloud provider options.

## Scope

### In Scope

- Create a minimal Docker Compose profile with web, API, worker, PostgreSQL/pgvector, Redis, MinIO and local/cloud provider options.
- Include setup, migration, admin seed and demo-data commands.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- All MVP epics

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

- [ ] Fresh Ubuntu-compatible installation follows documented commands.
- [ ] Local LLM path requires no proprietary credentials.
- [ ] Health page shows dependency status.

## Required Tests

### Unit and Contract Tests

- Clean-install smoke test
- Local-provider E2E
- Upgrade/migration smoke test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/deployment/minimal-self-host.md`

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
