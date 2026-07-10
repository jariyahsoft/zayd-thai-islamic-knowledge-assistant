# TASK-13-08 — Minimal Self-host Profile

## Status

`BLOCKED`

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

- `tasks/13_operations/13-08_minimal_self_host_profile.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- Dependency review: `tasks/00_task_index.md` records TASK-11-05 as `BLOCKED`, so EPIC-11 does
  not satisfy its all-tasks-complete gate and the `All MVP epics` dependency is unmet.

### Acceptance Criteria Result

- Blocked before implementation; acceptance criteria were not attempted.

### Security and License Review

- No code, configuration, secret, or deployment changes were made. Deferring a partial self-host
  profile avoids presenting an incomplete MVP as an installable release.

### Known Limitations

- Blocker: EPIC-11 is incomplete because TASK-11-05 is `BLOCKED`.
- Owner: EPIC-11 / TASK-11-05 owner.
- Next action: complete TASK-11-05 and the EPIC-11 completion gate, then retry TASK-13-08.

### Follow-up Tasks

- TASK-13-09 remains blocked by TASK-13-08.

### Commit

- No focused implementation commit; blocker records will be committed with the task-range
  bookkeeping.
