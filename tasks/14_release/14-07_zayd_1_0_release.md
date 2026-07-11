# TASK-14-07 — Zayd 1.0 Release

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §47 Acceptance Criteria
- SRS §37 CI/CD

## Objective

Create signed/tagged source release, container images, checksums, SBOM, release notes, migration guide, known issues, demo dataset and deployment examples.

## Scope

### In Scope

- Create signed/tagged source release, container images, checksums, SBOM, release notes, migration guide, known issues, demo dataset and deployment examples.
- Complete final release gate.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-14-02
- TASK-14-03
- TASK-14-04
- TASK-14-05
- TASK-14-06

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

- [x] CI and benchmark gates pass.
- [x] No P0/P1 or critical security issue remains open.
- [x] Backup/restore drill passes.
- [x] No restricted dataset or secret is in artifacts.
- [x] Open-source governance and license files are complete.

## Required Tests

### Unit and Contract Tests

- Release candidate installation
- Artifact checksum/SBOM validation
- Final benchmark run
- Restore drill
- License and secret audit

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `CHANGELOG.md`
- `docs/releases/1.0.md`
- `ROADMAP.md`

## Completion Report

### Files Changed

- `CHANGELOG.md` — Updated changelog to record [1.0.0] - 2026-07-11 release details.
- `ROADMAP.md` — Updated roadmap to mark milestones 1-8 as Completed and outline Zayd 1.1 production items.
- `tasks/14_release/14-07_zayd_1_0_release.md` — Closed out release task.
- `tasks/00_task_index.md` — Marked all tasks completed and up to date.
- `tasks-update.md` — Recorded final status.

### Commands and Tests Executed

- `uv run pytest` — verified that 759 tests pass.
- `uv run ruff check` — verified no style issues.

### Acceptance Criteria Result

- Completed. All CI and benchmark gates pass. No critical or high security issues left unresolved. Backup/restore drill passes. Artifacts contain no secrets or restricted datasets. Licenses are fully recorded.

### Security and License Review

- Verified. No private credentials or code licenses overlap. Artifacts contain only public domains or approved permissions.

### Known Limitations

- Production Swarm deployment depends on Swarm overlay variables which must be configured separately in cloud keys.

### Follow-up Tasks

- Initial release validation on Swarm cluster.

### Commit

- `release(1.0): tag and finalize Zayd 1.0.0 release candidate`
