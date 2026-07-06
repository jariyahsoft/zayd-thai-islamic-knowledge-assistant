# TASK-01-05 — Environment Configuration Validation

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-OSS-001 — `.env.example`
- SRS §44 Environment Configuration
- NFR-SEC-003 — Secrets must not be stored in repository
- NFR-SEC-013 — Secret scanning
- NFR-PRV-004 — Reduce personal data sent externally

## Objective

Create typed, validated and safely logged environment configuration for TypeScript applications and Python services.

## Scope

### In Scope

- Create root and service-specific `.env.example` files as appropriate.
- Define required and optional settings.
- Validate configuration at process startup.
- Mask secrets in logs and error output.
- Define development defaults that work with Docker Compose.
- Define feature flags for external providers, guest mode and local-only operation.

### Out of Scope

- Deploying a production secret manager.
- Adding real provider credentials.
- Creating production environment files.

## Dependencies

- TASK-01-04

## Expected Files

- Root `.env.example`
- Service-specific `.env.example` files where needed
- Shared TypeScript configuration validation module
- Shared Python configuration validation module
- Configuration reference documentation

## Required Configuration Categories

```text
Application
Database
Redis
Object storage
Authentication
LLM provider
Embedding provider
Default language
Default madhhab
Feature flags
Logging
```

## Functional Requirements

1. Missing required values must stop startup with a concise error.
2. Invalid URLs, ports, booleans and enumerations must be rejected.
3. Unknown provider names must be rejected unless registered through the plugin system.
4. `ENABLE_EXTERNAL_PROVIDERS=false` must support a local-only development profile.
5. Public frontend variables must be explicitly separated from server secrets.
6. Secret values must never appear in structured logs or exception representations.

## Technical Requirements

- Use schema validation suitable for each language stack.
- Generate or maintain a configuration reference document.
- Keep setting names consistent across services where they represent the same concept.
- Avoid implicit fallback to insecure production values.
- Validate configuration in CI using the example environment.

## Security Requirements

- Secret fields include passwords, signing keys, API keys, object-storage secrets and OAuth secrets.
- Development default credentials must trigger a warning outside development mode.
- Production mode must reject known development passwords and keys.
- Error messages may name missing variables but must not print their values.

## Acceptance Criteria

- [x] `.env.example` includes all settings needed for local startup.
- [x] Local Docker profile starts from copied example configuration.
- [x] Missing required settings stop startup.
- [x] Invalid settings stop startup.
- [x] Secret values are masked in logs.
- [x] Production mode rejects insecure development defaults.
- [x] External providers can be disabled completely.
- [x] Frontend bundles do not expose server-only values.

## Required Tests

### Unit Tests

- Required field missing.
- Invalid enum/provider.
- Invalid URL.
- Secret redaction.
- Production rejection of development credentials.

### Integration Tests

- Start services with valid example environment.
- Confirm failure with an intentionally invalid environment.
- Inspect built frontend for known server-secret test markers.

## Documentation Updates

- `docs/development/configuration.md`
- `.env.example` comments
- Root quick-start guide

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `.env.example`
- `apps/web/.env.example`
- `apps/reviewer/.env.example`
- `apps/admin/.env.example`
- `apps/web/package.json`
- `apps/reviewer/package.json`
- `apps/admin/package.json`
- `apps/web/app/env.client.test.ts`
- `apps/reviewer/app/env.client.test.ts`
- `apps/admin/app/env.client.test.ts`
- `apps/reviewer/app/page.tsx`
- `apps/admin/app/page.tsx`
- `packages/config/src/env/public.ts`
- `packages/config/src/env/public.test.ts`
- `packages/config/src/env/shared.ts`
- `packages/config/src/env/server.ts`
- `packages/config/src/env/server-core.ts`
- `packages/config/src/env/server-core.test.ts`
- `services/common/src/zayd_common/settings.py`
- `services/common/tests/test_settings.py`
- `services/api/src/zayd_service_api/app.py`
- `services/worker/src/zayd_service_worker/service.py`
- `infra/compose/development.yml`
- `docs/development/configuration.md`
- `docs/development/docker.md`
- `README.md`
- `scripts/check-frontend-env-leaks.sh`
- `tasks/01_foundation/01-05_environment_configuration_validation.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `corepack pnpm --filter @zayd/config test`
- `corepack pnpm test`
- `corepack pnpm typecheck`
- `corepack pnpm build`
- `~/.local/bin/uv run pytest services/common/tests/test_settings.py services/api/tests/test_api_imports.py services/worker/tests/test_worker_imports.py`
- `bash scripts/check-frontend-env-leaks.sh dev-jwt-secret-change-me`
- `docker compose config`
- `docker compose up -d --build api worker web reviewer admin`
- `docker compose ps`
- `docker compose exec -T api python -c "from zayd_common.settings import ServiceSettings; settings = ServiceSettings.from_runtime_env(app_name='api'); print(settings.environment); print(settings.enable_external_providers); print(settings.default_language)"`
- `docker compose exec -T worker python -c "from zayd_common.settings import ServiceSettings; settings = ServiceSettings.from_runtime_env(app_name='worker'); print(settings.environment); print(settings.enable_guest_mode)"`
- `curl --silent --show-error --fail http://localhost:8000/health`
- `NEXT_PUBLIC_API_BASE_URL='not-a-url' corepack pnpm --filter @zayd/web build`
- `env -i PATH=\"$PATH\" HOME=\"$HOME\" PYTHONPATH=\"services/common/src:services/api/src:services/worker/src\" ~/.local/bin/uv run python -c "... ServiceSettings.from_runtime_env(app_name='api') ..."`

### Acceptance Criteria Result

- Passed. The root example env now covers local startup, Compose consumes the shared variables, TypeScript and Python startup validation reject missing and invalid values, secret fields stay redacted, production mode blocks known development placeholders, local-only mode is enforced when external providers are disabled, and the frontend build artifacts were checked for leaked server-only secret markers.

### Security and License Review

- Reviewed for task scope. No real secrets were added; example credentials remain clearly marked as development-only placeholders. Secret-bearing Python fields use `SecretStr`, validation errors name variables without printing their values, and frontend validation is isolated to `NEXT_PUBLIC_*` variables. No new third-party source code or license obligations were introduced.

### Known Limitations

- The TypeScript server-side provider validation currently supports the built-in foundation providers and a future registration hook, but the plugin-backed provider registry itself is not implemented yet.
- Frontend build scripts inject the documented example public API base URL when not otherwise provided, so workspace builds remain reproducible while runtime validation still fails on invalid explicit values.
- Python placeholder services still share one common settings model; later service-specific tasks may split stricter per-service requirements.

### Follow-up Tasks

- `TASK-01-06` should expose the new validation and leak-check commands through a stable developer command surface such as `make` targets.
- Later provider/plugin tasks should connect runtime provider validation to the actual plugin registration source instead of the current built-in allowlists.

### Commit

- Not created in this task attempt.
