# TASK-01-03 — Initialize Python Services

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- SRS §7.2 Backend Technology Stack
- SRS §8 Monorepo Structure
- SRS §9 Provider Adapter Architecture
- SRS §37 CI/CD Requirements

## Objective

Initialize consistent Python service foundations for API, orchestration, retrieval, ingestion, worker and evaluation components using FastAPI-compatible tooling and strict quality checks.

## Scope

### In Scope

- Configure Python version and package management.
- Add shared Ruff, MyPy and Pytest configuration.
- Initialize service packages with health or placeholder entry points.
- Add Pydantic settings foundations without real secrets.
- Add shared logging interface placeholders.
- Add unit-test structure.

### Out of Scope

- Implementing business endpoints.
- Implementing provider adapters.
- Connecting to PostgreSQL or Redis.
- Implementing background tasks.

## Dependencies

- TASK-01-01

## Expected Files

```text
pyproject.toml
.python-version or .tool-versions
services/*/pyproject.toml or approved workspace configuration
services/*/src/...
services/*/tests/...
```

## Functional Requirements

1. The following commands must be available:

```bash
ruff check .
ruff format --check .
mypy .
pytest
```

2. Every initialized service must expose a minimal health or import check.
3. Shared configuration must not force services to import each other's internal modules.
4. Settings must be validated and typed.
5. Async code conventions must be documented.

## Technical Requirements

- Use a supported Python version, preferably 3.12 unless repository constraints require otherwise.
- Enable strict or near-strict MyPy settings for core packages.
- Define clear package namespaces.
- Avoid modifying `sys.path` at runtime.
- Configure pytest asyncio support where appropriate.
- Add coverage configuration with an initial threshold that can increase over time.

## Security Requirements

- Pydantic settings must redact secret values in representations and logs.
- No hard-coded provider tokens, database passwords or production URLs.
- Health endpoints must not disclose sensitive configuration.

## Acceptance Criteria

- [ ] Python environment installs from the chosen lock mechanism.
- [ ] `ruff check .` passes.
- [ ] `ruff format --check .` passes.
- [ ] `mypy .` passes.
- [ ] `pytest` passes.
- [ ] Each service package imports successfully.
- [ ] Secret settings are redacted.
- [ ] No internal service cross-imports violate architecture boundaries.

## Required Tests

- Unit test for settings validation.
- Unit test proving secret redaction.
- Import/health test for each initialized service.

## Documentation Updates

- `docs/development/python.md`
- Root developer setup documentation

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
