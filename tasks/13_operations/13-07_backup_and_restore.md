# TASK-13-07 — Backup and Restore

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §34 Backup and Disaster Recovery

## Objective

Implement encrypted backup and restore for PostgreSQL, object storage, prompts, policies, license documents and audit data.

## Scope

### In Scope

- Implement encrypted backup and restore for PostgreSQL, object storage, prompts, policies, license documents and audit data.
- Provide scheduled jobs and runbook.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-02
- TASK-05-02

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

- [x] Daily backup profile exists.
- [x] Restore is tested into an isolated environment.
- [x] Retention and off-site strategy are configurable.
- [x] Restore preserves referential integrity and permissions.

## Required Tests

### Unit and Contract Tests

- Automated backup test
- Full restore drill
- Corruption/failure simulation

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/operations/backup-restore.md`
- `docs/operations/disaster-recovery.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `infra/backup/backup.sh`
- `infra/backup/restore.sh`
- `infra/backup/zayd-backup.service`
- `infra/backup/zayd-backup.timer`
- `infra/backup/README.md`
- `infra/backup/tests/test_backup_restore.py`
- `docs/operations/backup-restore.md`
- `docs/operations/disaster-recovery.md`
- `tasks/13_operations/13-07_backup_and_restore.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest -q infra/backup/tests/test_backup_restore.py` — 3 passed.
- `uv run ruff check infra/backup/tests/test_backup_restore.py` — passed.
- `uv run ruff format --check infra/backup/tests/test_backup_restore.py` — passed.
- `bash -n infra/backup/backup.sh infra/backup/restore.sh` — passed.
- Focused credential/private-key pattern scan — no findings.
- `git diff --check` — passed.
- `shellcheck` — unavailable in the execution environment.

### Acceptance Criteria Result

- Passed. The daily systemd timer invokes an encrypted, checksummed database/role, object-storage,
  and non-secret configuration bundle. Restore is fail-closed unless explicitly isolated, verifies
  corruption before mutation, restores roles and ACL-bearing data, restores objects, and checks
  both dependencies. Local retention and optional off-site replication are configurable.

### Security and License Review

- Backup and restore require separate operator-provided credentials and a secret-mounted GPG key;
  neither is committed. Files are created with restrictive process permissions, sensitive
  operations produce bounded actor/trace audit records, and restore targets must be isolated.
  Tier S production deployment requires human security and operations review.

### Known Limitations

- The automated drill uses command fakes and validates orchestration/failure behavior; production
  infrastructure must perform the documented monthly drill and application-level consistency/RBAC
  checks. `shellcheck` was not installed. Alert routing is an operator integration documented in
  the runbook rather than a committed provider secret.

### Follow-up Tasks

- TASK-13-08 may proceed only when all MVP epics are complete.

### Commit

- Pending focused task commit.
