# TASK-01-05 — Environment Configuration Validation

## Status

`TODO`

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

- [ ] `.env.example` includes all settings needed for local startup.
- [ ] Local Docker profile starts from copied example configuration.
- [ ] Missing required settings stop startup.
- [ ] Invalid settings stop startup.
- [ ] Secret values are masked in logs.
- [ ] Production mode rejects insecure development defaults.
- [ ] External providers can be disabled completely.
- [ ] Frontend bundles do not expose server-only values.

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
