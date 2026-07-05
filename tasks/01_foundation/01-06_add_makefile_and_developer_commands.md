# TASK-01-06 — Add Makefile and Developer Commands

## Status

`TODO`

## Model Tier

Tier B

## Related Requirements

- FR-OSS-006 — Seed admin command
- FR-OSS-008 — Migration command
- FR-OSS-009 — Backup and restore scripts
- SRS §45 Installation Requirements
- SRS §37 CI/CD Requirements

## Objective

Provide a stable, documented command interface for common local-development and self-host operations regardless of the underlying TypeScript, Python and Docker tooling.

## Scope

### In Scope

Add a root `Makefile` or an equivalently portable documented command runner with these commands:

```bash
make setup
make dev
make stop
make logs
make migrate
make seed-admin
make seed-demo
make test
make test-unit
make test-integration
make lint
make typecheck
make format
make format-check
make build
make health
make backup
make restore
make clean
```

- Commands must delegate to workspace and Docker tools.
- Commands must fail on errors.
- Dangerous commands must require explicit confirmation or arguments.

### Out of Scope

- Implementing the final database migration logic.
- Implementing production backup policy.
- Implementing a full setup UI.
- Adding hidden destructive shortcuts.

## Dependencies

- TASK-01-05

## Expected Files

- Root `Makefile` or equivalent command runner
- Supporting scripts under the approved infrastructure or tooling directory
- Developer command documentation
- Git ignore entries for generated backup artifacts where needed

## Functional Requirements

1. `make setup` prepares dependencies and validates configuration.
2. `make dev` starts the local development stack.
3. `make stop` stops services without deleting data.
4. `make migrate` runs the current migration mechanism.
5. `make seed-admin` requires explicit admin identity input and never prints the password.
6. `make seed-demo` loads only redistributable demo data.
7. `make test`, `lint`, `typecheck` and `build` run across all applicable workspaces.
8. `make backup` and `restore` must clearly state that the initial implementation is for development until EPIC-13 completes production hardening.
9. `make clean` must not delete persistent data unless a separate confirmation variable is provided.

## Technical Requirements

- Use `.PHONY` targets.
- Use shell strict mode where scripts are involved.
- Avoid platform-specific commands where practical; document Linux as the supported baseline.
- Ensure commands work on Ubuntu Server.
- Print concise help using `make help`.

## Security Requirements

- Never echo passwords, tokens or complete connection strings.
- Destructive restore/reset commands require explicit target and confirmation.
- Demo seed data must contain no private, copyrighted or restricted content.
- Backup files must be ignored by Git.

## Acceptance Criteria

- [ ] `make help` lists documented commands.
- [ ] `make setup` completes on a clean supported environment.
- [ ] `make dev` starts the stack.
- [ ] `make stop` stops it without removing volumes.
- [ ] Quality commands delegate correctly to TypeScript and Python workspaces.
- [ ] Dangerous cleanup/restore actions require confirmation.
- [ ] Commands do not print secrets.
- [ ] Ubuntu installation documentation uses these commands consistently.

## Required Tests

- Run every non-destructive target.
- Verify error propagation by forcing a failing subcommand.
- Verify `make clean` preserves persistent volumes without explicit confirmation.
- Verify logs do not include secret test markers.

## Documentation Updates

- Root `README.md`
- `docs/development/commands.md`
- Ubuntu quick-start documentation

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
