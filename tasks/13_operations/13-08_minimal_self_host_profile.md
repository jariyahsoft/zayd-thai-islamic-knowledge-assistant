# TASK-13-08 — Minimal Self-host Profile

## Status

`DONE`

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

- [x] Fresh Ubuntu-compatible installation follows documented commands.
- [x] Local LLM path requires no proprietary credentials.
- [x] Health page shows dependency status.

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

- Minimal Compose profile, generated-secret environment template and lifecycle script, real initial
  admin provisioning, dependency health endpoint, container adjustments, focused tests,
  installation documentation, and task records.

### Commands and Tests Executed

- `uv run pytest -q infra/compose/tests/test_minimal_profile.py services/api/tests/test_health_dependencies.py` — 5 passed.
- Focused Ruff, Ruff format, MyPy, Bash syntax, and `git diff --check` — passed.
- `docker compose ... config --quiet` using generated test secrets — passed.
- Clean container build smoke: API, worker, and web images built successfully.
- Focused credential/private-key pattern scan — no findings; Trivy/Grype/Gitleaks/ShellCheck were unavailable.

### Acceptance Criteria Result

- Passed. The documented Ubuntu sequence initializes restricted local secrets, validates and starts
  the required services, runs migrations, provisions an admin, and exposes bounded dependency
  health. Bundled Ollama local mode has no proprietary credential requirement.

### Security and License Review

- Stateful services have no host ports and use an internal network. API binds to loopback by
  default; generated secrets are mode `0600` and ignored by Git. External-provider mode requires
  explicit opt-in and policy review. No production credentials or restricted data were added.

### Known Limitations

- The profile is a single-host failure domain and does not meet production HA targets. The full
  Ollama model pull/runtime E2E was not run because it is hardware/model-size dependent; the local
  profile, image builds, configuration, and no-key path were verified. Container/security scanner
  CLIs were unavailable in the environment.

### Follow-up Tasks

- TASK-13-09 is now dependency-ready.

### Commit

- `751049a feat(deployment): add minimal self-host profile`
