# TypeScript Workspaces

## Package Manager

Zayd uses `pnpm` workspaces for frontend applications and shared TypeScript packages. The supported Node.js version is pinned in `.nvmrc`.

## Workspace Rules

- Applications consume shared code through workspace package names such as `@zayd/ui` and `@zayd/contracts`.
- Shared packages expose explicit exports and do not allow private source path imports across package boundaries.
- TypeScript strict mode is enabled in `tsconfig.base.json`.
- Frontend apps must not import the server-only environment module from `@zayd/config/env/server`.

## Environment Separation

- Public browser-safe values belong in `NEXT_PUBLIC_*` variables and are read through `@zayd/config/env/public`.
- Server-only values must stay out of `NEXT_PUBLIC_*` and are isolated in `@zayd/config/env/server`.
- Do not import server-only environment modules into client bundles.

## Root Commands

- `corepack pnpm lint`
- `corepack pnpm typecheck`
- `corepack pnpm test`
- `corepack pnpm build`
- `corepack pnpm format:check`
