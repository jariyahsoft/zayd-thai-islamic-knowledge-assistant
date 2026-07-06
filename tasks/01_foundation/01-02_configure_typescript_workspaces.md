# TASK-01-02 — Configure TypeScript Workspaces

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §7.1 Frontend Technology Stack
- SRS §8 Monorepo Structure
- SRS §37 CI/CD Requirements
- SRS §38 Branching Strategy

## Objective

Configure consistent TypeScript workspaces for Zayd frontend applications and shared packages, including package management, linting, formatting, type checking and build scripts.

## Scope

### In Scope

- Configure `pnpm` workspaces.
- Add root `package.json` scripts.
- Add shared TypeScript configurations.
- Configure ESLint and Prettier.
- Configure path and package exports.
- Initialize minimal buildable packages/apps without product features.
- Add environment type placeholders for public frontend values.

### Out of Scope

- Building production pages.
- Adding authentication.
- Implementing API clients beyond placeholders.
- Adding proprietary UI libraries without approval.

## Dependencies

- TASK-01-01

## Expected Files

```text
package.json
pnpm-workspace.yaml
pnpm-lock.yaml
tsconfig.base.json
eslint.config.*
.prettierrc*
.prettierignore
apps/*/package.json
packages/*/package.json
```

## Functional Requirements

1. Root commands must include:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm format:check
```

2. Shared packages must expose explicit package exports.
3. Applications must consume shared packages through workspace dependencies.
4. TypeScript strict mode must be enabled unless an exception is documented.
5. Frontend environment variables must distinguish server-only and public values.

## Technical Requirements

- Use a supported Node.js LTS version recorded in `.nvmrc` or `.tool-versions`.
- Avoid TypeScript path aliases that work only in editors but fail at runtime.
- Use consistent module settings across workspaces.
- Do not allow importing private source paths from another package.
- Configure linting for React hooks and TypeScript correctness.

## Security Requirements

- Do not expose server secrets through `NEXT_PUBLIC_*` variables.
- Add lint or documentation rules preventing accidental secret imports into client bundles.
- Dependency versions must be pinned through the lock file.

## Acceptance Criteria

- [ ] `pnpm install --frozen-lockfile` succeeds after lock file creation.
- [ ] `pnpm lint` passes.
- [ ] `pnpm typecheck` passes.
- [ ] `pnpm test` passes with initial placeholder tests.
- [ ] `pnpm build` builds all initialized TypeScript workspaces.
- [ ] Strict TypeScript is enabled.
- [ ] Client/server environment separation is documented.

## Required Tests

- Build each application separately.
- Build each shared package separately.
- Add at least one test proving a shared contract can be imported by an app.
- Confirm a server-only environment module cannot be imported from a client module.

## Documentation Updates

- `docs/development/typescript.md`
- Root `README.md` developer commands

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `package.json`
- `pnpm-workspace.yaml`
- `pnpm-lock.yaml`
- `.nvmrc`
- `tsconfig.base.json`
- `eslint.config.mjs`
- `.prettierrc.json`
- `.prettierignore`
- `apps/tsconfig.json`
- `packages/tsconfig.json`
- `apps/*/package.json`
- `apps/*/tsconfig.json`
- `apps/*/next-env.d.ts`
- `apps/*/app/*`
- `apps/*/.env.example`
- `packages/*/package.json`
- `packages/*/tsconfig.json`
- `packages/*/src/*`
- `docs/development/typescript.md`
- `README.md`
- `tasks/01_foundation/01-02_configure_typescript_workspaces.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `sed -n '1,280p' tasks/01_foundation/01-02_configure_typescript_workspaces.md`
- `sed -n '1,220p' package.json`
- `sed -n '1,220p' pnpm-workspace.yaml`
- `sed -n '1,220p' pyproject.toml`
- `node -v`
- `corepack --version`
- `corepack pnpm --version`
- `corepack pnpm view ...` for pinned tool and framework versions
- `corepack pnpm install`
- `corepack pnpm install --frozen-lockfile`
- `corepack pnpm lint`
- `corepack pnpm typecheck`
- `corepack pnpm test`
- `corepack pnpm build`

### Acceptance Criteria Result

- Passed: `pnpm install --frozen-lockfile` succeeds after lock file creation.
- Passed: `pnpm lint` passes.
- Passed: `pnpm typecheck` passes.
- Passed: `pnpm test` passes with initial placeholder tests.
- Passed: `pnpm build` builds all initialized TypeScript workspaces.
- Passed: strict TypeScript is enabled in `tsconfig.base.json`.
- Passed: client/server environment separation is documented in `docs/development/typescript.md` and enforced by package structure and lint restrictions.

### Security and License Review

- No server secrets are exposed through `NEXT_PUBLIC_*` variables.
- Public and server-only environment modules are separated in `@zayd/config`.
- Lint rules restrict client imports of `@zayd/config/env/server`.
- Dependency versions are pinned through `pnpm-lock.yaml`.
- No third-party source code was copied into the repository.

### Known Limitations

- The app workspaces are minimal placeholders and do not implement product features yet.
- The root worktree still contains earlier uncommitted files from prior tasks, including `.github/` and `tasks/.00_task_index.md.swp`, which were left untouched.

### Follow-up Tasks

- `TASK-01-03` should initialize Python services to match the frontend workspace foundation.
- `TASK-01-04` can add Docker Compose after both TypeScript and Python workspace initialization are complete.

### Commit

- Pending focused commit creation
