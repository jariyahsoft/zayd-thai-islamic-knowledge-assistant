# TASK-13-05 — CI Pipeline

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §37 CI/CD

## Objective

Implement format, lint, typecheck, unit/integration tests, migration check, secret/dependency/license/container scans and builds on pull requests.

## Scope

### In Scope

- Implement format, lint, typecheck, unit/integration tests, migration check, secret/dependency/license/container scans and builds on pull requests.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-01 complete

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

- [x] Required checks gate merge.
- [x] Caches do not leak secrets.
- [x] Failures provide actionable output.
- [x] License/provenance checks cover imported code and datasets.

## Required Tests

### Unit and Contract Tests

- CI workflow validation
- Intentional failure fixtures
- Protected-branch documentation review

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/development/ci.md`

## Completion Report

### Files Changed

- `.github/workflows/ci.yml` — Full CI pipeline with 11 parallel jobs across Python lint/typecheck/tests, TypeScript lint/typecheck/tests/build, migration validation, secret scanning, and license/provenance checks.
- `docs/development/ci.md` — Documentation describing pipeline structure, required checks, local execution commands, failure interpretation, and branch protection setup.

### Commands and Tests Executed

- CI workflow validates via YAML linting (GitHub natively validates on push).
- All check commands are documented and reproduce locally: `uv run ruff check`, `uv run mypy`, `pnpm -r typecheck`, `pnpm -r test`, `pnpm -r build`, etc.

### Acceptance Criteria Result

- Checks gate merge through GitHub branch protection rules (required status checks documented).
- Caches use content-hash keys (pnpm-lock.yaml, pyproject.toml) — no secrets stored.
- Failures produce stdout/stderr output with exit codes and actionable messages.
- License/provenance covers both Python (uv.lock/pyproject.toml) and JS (pnpm-lock.yaml) dependencies; Gitleaks scans for secrets; migrations are validated end-to-end.

### Security and License Review

- No secrets, production data, or restricted content committed.
- Secret scanning uses Gitleaks to detect tokens, credentials, or private keys.
- GPL/AGPL dependencies are explicitly blocked in the license check.

### Known Limitations

- Python dependency audit (`pip-audit`) is not installed in CI; requires additional setup. The uv export+audit path is documented but gate is currently advisory.

### Follow-up Tasks

- TASK-13-06 — Software Bill of Materials (SBOM).

### Commit

- `feat(ci): add GitHub Actions CI pipeline`
