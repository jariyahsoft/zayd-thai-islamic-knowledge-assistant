# TASK-13-09 — Production Deployment Profile

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §43.3 Production
- NFR-AVL-001

## Objective

Provide production reference architecture for reverse proxy/load balancer, replicas, health probes, worker isolation, managed secrets, monitoring and backups.

## Scope

### In Scope

- Provide production reference architecture for reverse proxy/load balancer, replicas, health probes, worker isolation, managed secrets, monitoring and backups.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-13-08

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

- [x] No default insecure credentials.
- [x] Rolling/canary deployment and rollback are documented.
- [x] Stateful components and failure domains are explicit.

## Required Tests

### Unit and Contract Tests

- Production compose/manifests validation
- Failover/health probe tests
- Security configuration review

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/deployment/production.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Production Compose/Swarm reference, TLS reverse proxy, replicated app/worker policies, external
  managed secrets, worker/network isolation, Prometheus configuration and endpoint, backup image/job,
  fail-closed secret loader, tests, production runbook, and task records.

### Commands and Tests Executed

- `uv run pytest -q infra/compose/tests/test_production_profile.py services/api/tests/test_health_dependencies.py infra/backup/tests/test_backup_restore.py` — 9 passed.
- Focused Ruff, Ruff format, MyPy, Bash syntax, Compose config, and `git diff --check` — passed.
- Production Nginx TLS configuration test in pinned container — passed.
- Production backup image build and required-tool smoke test — passed.
- Focused secret/private-key scan — no findings; Trivy/Grype/Gitleaks/ShellCheck/Docker Scout were unavailable.

### Acceptance Criteria Result

- Passed. All credential-bearing fields use external secret files with a fail-closed loader; app,
  proxy, and worker replicas have health checks, spread/rolling/automatic rollback policies; canary
  and rollback procedures are documented; managed state and failure domains are explicit.

### Security and License Review

- No default credentials or production data are present. TLS, internal app/operations networks,
  worker edge isolation, rate limits, bounded metrics, external secrets/volumes, non-root backup,
  encrypted off-site backup, and immutable image-tag requirements are represented. Tier S human
  security/platform review is still required before production approval.

### Known Limitations

- The reference depends on environment-provided managed HA PostgreSQL, Redis, object storage, WAF/LB,
  secret manager, durable monitoring volume, node labels, signed images, and real certificates.
  Stateful failover, load, canary, penetration, and restore drills require the target environment.
  Container vulnerability scanners were unavailable locally.

### Follow-up Tasks

- TASK-14-01 Pilot Environment is now dependency-ready. Complete environment-specific human security,
  platform, DBA, and operations review before production use.

### Commit

- Focused task commit created; see Git history for the commit identifier.
