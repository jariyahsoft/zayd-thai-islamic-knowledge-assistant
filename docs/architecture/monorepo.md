# Monorepo Architecture

## Purpose

Zayd uses a monorepo to keep frontend apps, Python services, shared TypeScript packages, plugins, database assets, infrastructure, and documentation in one auditable repository.

## Layer Ownership

- `apps/*`: frontend applications owned by frontend maintainers.
- `services/*`: backend services owned by backend, retrieval, ingestion, worker, and evaluation maintainers.
- `packages/*`: shared TypeScript packages owned by platform maintainers.
- `plugins/*`: provider and storage adapters owned by provider integration maintainers.
- `database/*`: migrations, schemas, seeds, and database tests owned by database maintainers.
- `infra/*`: local and deployment infrastructure owned by operations maintainers.
- `docs/*`: requirements, architecture, development, deployment, governance, and security documentation owned by the relevant policy maintainers.

## Dependency Rules

1. Frontend apps may depend on shared packages and API clients, but may not connect directly to PostgreSQL, Redis, object storage, or provider SDK implementations.
2. `services/api` exposes authenticated HTTP and SSE boundaries and must not import provider SDK implementations directly.
3. `services/orchestrator` may depend on provider interfaces, retrieval contracts, and policy contracts.
4. `services/retrieval` owns retrieval implementation and does not own user-interface logic.
5. Provider-specific code belongs under `plugins/*` and implements interfaces from `packages/provider-sdk` or `packages/plugin-sdk`.
6. `database/*` owns database artifacts only; business logic belongs in services and packages.
7. Shared packages must not depend on apps or service implementation modules.
8. Religious policy and license policy enforcement remain server-side.
9. Plugin loading must be explicit allow-list behavior, not arbitrary runtime execution.
10. Restricted datasets, production payloads, user conversations, and credentials must not be committed.

## Workspace Commands

Root placeholder commands exist for:

- `npm run build`
- `npm run lint`
- `npm run typecheck`
- `npm test`

Later tasks will replace placeholders with workspace-aware implementations after TypeScript and Python tooling are configured.
