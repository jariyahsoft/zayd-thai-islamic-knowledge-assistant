# TASK-01-01 — Create Monorepo Structure

## Status

`TODO`

## Model Tier

Tier S

## Related Requirements

- SRS §8 Monorepo Structure
- SRS §3 Modular Architecture
- FR-OSS-004 — Operate without proprietary services
- FR-OSS-011 — Provider development guide
- FR-OSS-012 — Plugin template

## Objective

Create the initial Zayd monorepo structure with clear dependency boundaries for frontend applications, Python services, shared packages, plugins, database assets, infrastructure and documentation.

## Scope

### In Scope

Create the following high-level structure:

```text
apps/web
apps/reviewer
apps/admin
services/api
services/orchestrator
services/retrieval
services/ingestion
services/worker
services/evaluation
packages/ui
packages/contracts
packages/api-client
packages/config
packages/provider-sdk
packages/plugin-sdk
plugins/llm
plugins/embeddings
plugins/vector-stores
plugins/knowledge-providers
plugins/auth-providers
plugins/storage
database/migrations
database/seeds
database/schemas
infra/docker
infra/compose
infra/nginx
infra/monitoring
infra/scripts
docs/architecture
docs/api
docs/development
docs/deployment
docs/governance
docs/security
```

- Add placeholder README files explaining ownership and intended responsibilities.
- Define dependency rules between layers.
- Add root scripts/placeholders for build, lint, test and type check.

### Out of Scope

- Implementing application features.
- Choosing production models.
- Creating database schema migrations.
- Implementing Docker Compose services.
- Importing code from Ansari, Criterion or other repositories.

## Dependencies

- TASK-00-01 through TASK-00-04 must be `DONE`.

## Architecture Boundaries

1. `apps/*` may depend on shared TypeScript packages and generated API clients.
2. `services/api` may call domain/application interfaces but must not import provider SDK implementations directly.
3. `services/orchestrator` may depend on provider interfaces, retrieval contracts and policy contracts.
4. `services/retrieval` owns retrieval implementation and must not own user-interface logic.
5. `plugins/*` implement interfaces from provider/plugin SDK packages.
6. `database/*` owns migrations and schema artifacts; business logic must not live there.
7. No frontend application may connect directly to PostgreSQL, Redis or object storage.
8. No restricted dataset may be committed to the monorepo.

## Expected Files

- Directory tree listed above.
- Root workspace manifests/placeholders.
- Architecture boundary document.
- README in each major directory.

## Functional Requirements

- Every major workspace must have a declared purpose and owner category.
- Root commands must be designed to run all workspaces without relying on global package installations.
- The structure must support independent frontend and Python-service builds.
- Plugins must be replaceable without changing core business logic.

## Technical Requirements

- Prefer a single JavaScript package manager for all TypeScript workspaces.
- Python services may use a shared tool configuration while remaining independently deployable.
- Define naming conventions for packages and services.
- Add architecture dependency rules that can later be enforced by linting or CI.

## Security Requirements

- No secret files.
- No provider credentials.
- No production URLs.
- No real religious corpus or user data.
- Plugin loading must be designed as an explicit allow-list, not arbitrary runtime execution.

## Acceptance Criteria

- [ ] Directory structure matches the approved SRS.
- [ ] Each major directory contains a purpose README.
- [ ] Dependency boundaries are documented.
- [ ] Root placeholder commands exist for build, lint, typecheck and test.
- [ ] No circular ownership/dependency design is introduced.
- [ ] No third-party source code is copied without provenance records.
- [ ] No restricted data or secrets are present.

## Required Tests

### Structural Checks

- Script verifies all required directories exist.
- Script verifies no unexpected `.env` or credential files are tracked.

### Architecture Review

- Tier S or human architect reviews dependency boundaries.
- License/provenance review confirms no unrecorded copied code.

## Documentation Updates

- `docs/architecture/monorepo.md`
- Root `README.md`
- Major-directory README files

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
