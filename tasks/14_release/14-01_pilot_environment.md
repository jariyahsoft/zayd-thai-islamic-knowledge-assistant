# TASK-14-01 — Pilot Environment

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §21 Phase 3
- SRS §43 Deployment Profiles

## Objective

Provision an isolated pilot environment with approved dataset, monitoring, limited users and separate secrets/storage.

## Scope

### In Scope

- Provision an isolated pilot environment with approved dataset, monitoring, limited users and separate secrets/storage.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-13 complete

## Expected Files

- Implementation files under the relevant `14_release` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use release-candidate versions and isolated environments.
- Document evidence for every release gate.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Use isolated pilot/release credentials and data.

## Acceptance Criteria

- [x] Pilot data cannot leak into production or public datasets.
- [x] Access is invite-only and auditable.
- [x] Monitoring and backup are operational.

## Required Tests

### Unit and Contract Tests

- Environment isolation tests
- Access-control smoke test
- Backup smoke test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/pilot/environment.md`

## Completion Report

### Files Changed

- `infra/compose/pilot.yml` — Configured pilot overlay, forcing environment isolation, separate named secrets, volumes, and invite-only configurations (disabled guest mode). Fixes duplicate S3 environment key syntax errors.
- `infra/scripts/validate-pilot-environment.sh` — Deployment script that enforces secret namespaces, approvals, and checksum verification of approved datasets.
- `docs/pilot/environment.md` — Documented closed pilot, isolation rules, registration limits, and operations checklist.
- `.env.pilot.example` — Template env parameters.
- `services/api/tests/test_pilot_access_api.py` — Integration test for invite-only control flows.
- `infra/compose/tests/test_pilot_profile.py` — Integration test for pilot configuration integrity checks.

### Commands and Tests Executed

- `uv run pytest infra/compose/tests/ infra/backup/tests/ services/api/tests/test_pilot_access_api.py`
- Checked script file executing bit: `chmod +x infra/scripts/validate-pilot-environment.sh`
- Verified configuration parsing: `docker compose -f infra/compose/production.yml -f infra/compose/pilot.yml config` (via python tests).

### Acceptance Criteria Result

- Completed. Enforces strict schema level isolation for secrets, volumes, database, and storage parameters. User lists are validated against hashed allow-lists, rejecting guests and logging audit trails. Backups and data isolation are covered by separate compose specifications.

### Security and License Review

- Verified. No raw client details, emails, or credentials are saved. Hashed allow-list comparison is used for verification.

### Known Limitations

- Real Cloud Docker stack deployments require manual credentials seeding in target registry structures.

### Follow-up Tasks

- TASK-14-02 — Scholar Pilot Workflow.

### Commit

- `feat(release): configure isolated pilot environment overlay`
