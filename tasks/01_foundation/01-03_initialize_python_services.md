# TASK-01-03 — Initialize Python Services

## Status

`DONE`

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

- `.python-version`
- `pyproject.toml`
- `uv.lock`
- `services/common/**`
- `services/api/pyproject.toml`
- `services/api/src/**`
- `services/api/tests/**`
- `services/orchestrator/pyproject.toml`
- `services/orchestrator/src/**`
- `services/orchestrator/tests/**`
- `services/retrieval/pyproject.toml`
- `services/retrieval/src/**`
- `services/retrieval/tests/**`
- `services/ingestion/pyproject.toml`
- `services/ingestion/src/**`
- `services/ingestion/tests/**`
- `services/worker/pyproject.toml`
- `services/worker/src/**`
- `services/worker/tests/**`
- `services/evaluation/pyproject.toml`
- `services/evaluation/src/**`
- `services/evaluation/tests/**`
- `docs/development/python.md`
- `README.md`
- `tasks/01_foundation/01-03_initialize_python_services.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `sed -n '1,300p' tasks/01_foundation/01-03_initialize_python_services.md`
- `sed -n '52,64p' tasks/00_task_index.md`
- `git status --short`
- `find services -maxdepth 2 -type f`
- `python3 --version`
- `python3 -m pip index versions ...`
- `python3 -m pip install --user --break-system-packages uv==0.11.26`
- `~/.local/bin/uv lock`
- `~/.local/bin/uv sync`
- `~/.local/bin/uv sync --frozen`
- `~/.local/bin/uv run ruff check .`
- `~/.local/bin/uv run ruff format --check .`
- `~/.local/bin/uv run mypy .`
- `~/.local/bin/uv run pytest`

### Acceptance Criteria Result

- Passed: Python environment installs from the chosen lock mechanism using `uv lock` and `uv sync --frozen`.
- Passed: `ruff check .` passes.
- Passed: `ruff format --check .` passes.
- Passed: `mypy .` passes.
- Passed: `pytest` passes.
- Passed: each service package imports successfully through service-specific tests.
- Passed: secret settings are redacted.
- Passed: no internal service cross-imports violate the initialized architecture boundaries.

### Security and License Review

- Typed settings use `SecretStr`, and secret values are redacted in representations.
- No hard-coded provider tokens, database passwords, or production URLs were introduced.
- Health placeholders return only service name and status.
- No copied third-party application code was added.

### Known Limitations

- `uv` had to be installed with `pip --user --break-system-packages` because the machine lacks `venv` support and uses a PEP 668 managed Python installation.
- Service entry points are placeholders only; they do not implement business endpoints, provider adapters, or infrastructure integration yet.
- The worktree still contains earlier uncommitted TypeScript and `.github` changes plus `tasks/.00_task_index.md.swp`, which were left untouched.

### Follow-up Tasks

- `TASK-01-04` can now add Docker Compose for both TypeScript and Python workspaces.
- Later service tasks should replace placeholder health and settings modules with domain-specific implementations.

### Commit

- Pending focused commit creation
