# CI Pipeline

The Zayd monorepo uses GitHub Actions for continuous integration. The workflow is defined in `.github/workflows/ci.yml`.

## What the Pipeline Runs

On every pull request targeting `main` (and on push to `main`), the pipeline executes these checks in parallel where possible:

| Job | Layer | Tool | Why |
|-----|-------|------|-----|
| `python_lint` | Python | ruff check + ruff format --check | Enforces style rules and import ordering |
| `python_typecheck` | Python | mypy (strict mode) | Catches type errors before runtime |
| `python_tests` | Python | pytest + coverage (≥70%) | Unit and integration tests with PostgreSQL |
| `ts_lint` | TypeScript | prettier + eslint | Consistent formatting and code quality |
| `ts_typecheck` | TypeScript | tsc (--noEmit) | Type-safety for TS packages and apps |
| `ts_tests` | TypeScript | vitest | Unit tests for front-end and shared packages |
| `ts_build` | TypeScript | pnpm -r build | Confirms every package/app compiles |
| `migration_check` | SQL | psql | Applies all up-migrations in order |
| `secret_scan` | Repo | Gitleaks | Prevents credentials/tokens from leaking |
| `license_check` | Mixed | pnpm licenses + uv export | Checks dependency license compatibility |

## Required Checks

Before a pull request can be merged to `main`, the following **branch protection rules** must be configured in the GitHub repository settings under `Settings > Branches > Add rule` (for the `main` branch):

1. **Require status checks to pass before merging** — enable the following status checks:
   - `python_lint`
   - `python_typecheck`
   - `python_tests`
   - `ts_lint`
   - `ts_typecheck`
   - `ts_tests`
   - `ts_build`
   - `migration_check`
   - `secret_scan`
2. **Require branches to be up to date** — ensures the PR branch is rebased on latest `main` before merge.
3. **Do not allow bypassing the above settings** — prevents force-pushes from skipping CI.
4. (Recommended) **Require signed commits** for an auditable chain of trust.

## Running Checks Locally

The same tools run in CI can be executed locally:

### Python

```bash
# Lint and format
uv run ruff check .
uv run ruff format --check .

# Type check
uv run mypy .

# Tests with coverage
uv run coverage run -m pytest
uv run coverage report
```

### TypeScript

```bash
# Lint and format
pnpm format:check
pnpm -r lint

# Type check
pnpm -r typecheck

# Tests
pnpm -r test

# Build
pnpm -r build
```

### Migrations

To validate migrations locally (requires a running PostgreSQL instance):

```bash
for migration in database/migrations/*.up.sql; do
  psql -h localhost -U zayd_dev -d zayd_dev -f "$migration"
done
```

## Interpreting Failures

- **Ruff/lint errors**: Fix the reported style issues or formatting. Use `uv run ruff check --fix .` to auto-fix most issues.
- **Mypy type errors**: Add type annotations or fix the reported type mismatch. If a third-party package lacks stubs, add it to `[[tool.mypy.overrides]]` in `pyproject.toml`.
- **Test failures**: Review the test log output. The `--tb=short` flag in CI keeps output concise; reproduce locally with `uv run pytest -k <test_name> -v` for full detail.
- **Coverage drop**: The `fail_under = 70` threshold is configured in `pyproject.toml`. If coverage drops below 70%, add tests for uncovered lines.
- **Secret scan warnings**: Never commit secrets, tokens, or private keys. If a false positive is triggered, add an exclusion to `.gitleaks.toml` (see Gitleaks docs).
- **Migration failures**: Ensure new migrations are numerically ordered (e.g., `0014_*.sql`) and both `.up.sql` and `.down.sql` files exist. Test the rollback path locally.

## Cache Strategy

- **Python (uv)**: `astral-sh/setup-uv` caches the uv download and the `.venv` based on `**/pyproject.toml` checksums.
- **TypeScript (pnpm)**: `actions/cache` stores `node_modules` using the `pnpm-lock.yaml` hash as the cache key.
- **Docker**: Layer caching is not configured in CI; build times are acceptable for the few Docker images.

## Adding New Checks

1. Add a new job block to `.github/workflows/ci.yml` under the appropriate section.
2. If the check should gate merging, add its job name to the branch protection rule's required status checks list in GitHub settings.
3. Document the check in this file under the "What the Pipeline Runs" table.
