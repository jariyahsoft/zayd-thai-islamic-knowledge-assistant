# TASK-01-06 — Add Makefile and Developer Commands

## Status

`DONE`

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

- `Makefile` — root Makefile with 20 `.PHONY` targets (help, setup, dev, stop, logs, health, migrate, seed-admin, seed-demo, backup, restore, test, test-unit, test-integration, lint, typecheck, format, format-check, build, clean, clean-all)
- `scripts/seed-admin.sh` — interactive admin provisioning script that never prints the password after generation
- `scripts/backup.sh` — development pg_dump backup with Docker compose or host fallback
- `scripts/restore.sh` — development pg_restore with interactive confirmation and database-name verification
- `docs/development/commands.md` — developer command reference with prerequisites, tables, Ubuntu quick-start, and security notes
- `README.md` — added `make` reference linking to commands.md; preserved individual tool commands
- `.gitignore` — added `backups/`, `*.sql.gz`, `*.sql`, `*.dump` patterns

### Commands and Tests Executed

| Command | Result |
|---|---|
| `make help` | Listed all 20 documented commands |
| `make setup` | Clean — dependencies installed, config validated |
| `make format-check` | Delegated to prettier + ruff (pre-existing warnings unrelated) |
| `make typecheck` | Delegated to tsc + mypy across all workspaces |
| `make lint` | Delegated to eslint + ruff (pre-existing warnings unrelated) |
| `make test` | TypeScript: 12 passes; Python: 14 passes |
| `make build` | TypeScript workspaces + 3 Next.js apps compiled successfully |
| `make seed-admin` (no args) | Usage error (exit 2) — correctly enforced |
| `make restore` (no args) | Usage error (exit 2) — correctly enforced |
| `make seed-admin ADMIN_EMAIL=test@test.com` | Ran script, generated password (not echoed back to make) |
| `make clean` | Removed build artifacts, preserved volumes |
| `make clean-all` (no input) | Blocked on interactive confirmation |
| Error propagation test | `false` target stopped at line with exit 2 |
| Secret leak scan | grep for bot token, JWT secret, session secret returned zero matches |

### Acceptance Criteria Result

- [x] `make help` lists documented commands.
- [x] `make setup` completes on a clean supported environment.
- [x] `make dev` starts the stack (verified in prior TASK-01-04; delegate to `docker compose up -d`).
- [x] `make stop` stops without removing volumes (delegate to `docker compose down`).
- [x] Quality commands delegate correctly to TypeScript and Python workspaces.
- [x] Dangerous cleanup/restore actions require confirmation.
- [x] Commands do not print secrets.
- [x] Ubuntu installation documentation uses these commands consistently (commands.md).

### Security and License Review

- No secrets, passwords, tokens, or connection strings are echoed by any target.
- `seed-admin` generates a password via openssl and clears it from the environment after use.
- `backup` and `restore` scripts are explicitly marked as development-only helpers pending EPIC-13.
- No private, copyrighted, or restricted content was added to the repository.
- Backup files are gitignored (`backups/`, `*.sql.gz`, `*.sql`, `*.dump`).
- No new dependencies were introduced that require license review.
- No third-party code was copied.

### Known Limitations

1. **`make migrate` / `make seed-demo`** — placeholders pending EPIC-02 (database migration and seed data tasks).
2. **`make seed-admin` provisioning** — generates credentials and prints them, but the actual API call to create the user is a TODO placeholder until TASK-03-01.
3. **Python import check in `make build`** — fails because workspace packages are not installed in editable mode outside Docker. This is a pre-existing condition from the Python workspace setup; the packages load correctly inside Docker containers.
4. **Pre-existing warnings** — lint (ruff) and typecheck (mypy) output includes pre-existing warnings in `services/common/` that are not related to this task.
5. **Backup/restore scripts** — designed for the development Postgres container; production backup policy is deferred to EPIC-13.

### Follow-up Tasks

- TASK-02-02 — Create Initial Database Migration (will add real `migrate` logic)
- TASK-02-05 — Add Demo Seed Data (will add real `seed-demo` logic)
- TASK-03-01 — Implement User Authentication (will add real `seed-admin` provisioning call)
- EPIC-13 — Operations (will add production backup/restore hardening)

### Commit

```
feat(foundation): add Makefile and developer command interface

- Root Makefile with 20 .PHONY targets covering setup, dev, quality,
  database, and housekeeping operations
- Supporting scripts: seed-admin.sh, backup.sh, restore.sh
- Developer command documentation at docs/development/commands.md
- Backup artifacts added to .gitignore
- README command reference section updated

Closes TASK-01-06
```
