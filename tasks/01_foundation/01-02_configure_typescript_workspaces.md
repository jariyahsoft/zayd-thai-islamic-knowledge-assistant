# TASK-01-02 — Configure TypeScript Workspaces

## Status

`TODO`

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
