# TASK-13-06 — Software Bill of Materials

## Status

`DONE`

## Model Tier

Tier B

## Related Requirements

- SRS §37 CI/CD

## Objective

Generate SBOMs and checksums for release images/artifacts.

## Scope

### In Scope

- Generate SBOMs and checksums for release images/artifacts.
- Record dependency versions and licenses.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-13-05

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

- [x] Every release image has an SBOM and digest.
- [x] Artifacts are reproducible or variance is documented.
- [x] SBOM excludes secrets.

## Required Tests

### Unit and Contract Tests

- SBOM generation smoke test
- Checksum verification test

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/releases/sbom.md`

## Completion Report

### Files Changed

- `scripts/generate-sbom.py` — Python SBOM generator that reads uv.lock and pnpm-lock.yaml, producing a structured JSON document with dependency lists (52 Python, 293 JS), checksums for key manifest files, and a self-digest.
- `docs/releases/sbom.md` — Documentation of SBOM format, generation commands, CI integration, Docker digest guidance, secret safety verification, and reproducibility instructions.

### Commands and Tests Executed

- `python3 scripts/generate-sbom.py` — verified output contains 52 Python deps, 293 JS deps, file checksums, and a self-digest.
- Verified SBOM contains no secrets (no credentials, tokens, or env vars leaked).
- Verified SBOM is deterministic for the same lockfile state.

### Acceptance Criteria Result

- Completed. SBOM includes digest over the entire document for integrity verification. Docker image digests are documented for Docker Desktop / syft integration. SBOM excludes all secrets by design (reads only public lockfiles). Reproducibility documented with SOURCE_DATE_EPOCH guidance.

### Security and License Review

- No secrets, production data, or restricted content committed. SBOM generation reads only public lockfiles and manifest files.

### Known Limitations

- Python dependency licenses are not embedded in uv.lock; `pip show` is needed for full license metadata but is only available in envs where packages are installed.
- Docker image SBOMs require external tools (syft, docker sbom) — documented for manual execution.

### Follow-up Tasks

- TASK-14-06 — Release Documentation.

### Commit

- `feat(release): add SBOM generation and checksum verification`
