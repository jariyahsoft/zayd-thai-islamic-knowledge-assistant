# TASK-00-01 — Initialize Git Repository

## Status

`READY`

## Model Tier

Tier B

## Related Requirements

- SRS §4 Open Source Structure
- FR-OSS-001 — Start from documented example configuration
- FR-OSS-010 — Provide self-host documentation foundations
- SRS §38 Branching Strategy
- SRS §40 Community Files

## Objective

Create a clean and predictable Git repository foundation for the Zayd open-source monorepo. Establish repository hygiene, line-ending rules and commit conventions before application code is introduced.

## Scope

### In Scope

- Initialize the Git repository if it does not already exist.
- Add a root `.gitignore` covering Node.js, Python, environment files, local databases, IDE files, test output and generated artifacts.
- Add `.editorconfig` with UTF-8, LF line endings and sensible indentation defaults.
- Add `.gitattributes` to normalize text files and protect binary assets from line-ending conversion.
- Add a short Conventional Commits guide.
- Add a minimal root `README.md` placeholder if one does not yet exist.
- Document the recommended protected-branch settings for `main`.

### Out of Scope

- Selecting the final source-code license.
- Creating GitHub issue templates.
- Creating application workspaces.
- Configuring CI/CD.
- Adding real secrets or production configuration.

## Dependencies

None.

## Expected Files

```text
.gitignore
.editorconfig
.gitattributes
README.md
CONTRIBUTING.md or docs/development/commits.md
```

## Functional Requirements

1. Source files must use UTF-8 and LF line endings.
2. `.env`, `.env.*` and secret files must be ignored, while `.env.example` remains trackable.
3. Generated build, test and cache directories must not be tracked.
4. The repository must document Conventional Commit prefixes at minimum: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci` and `security`.
5. The recommended default branch must be `main`.

## Technical Requirements

- Do not ignore lock files.
- Do not ignore database migration files.
- Do not ignore documentation or task files.
- Include patterns for `node_modules`, `.next`, `dist`, `coverage`, `.venv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, local MinIO data and local PostgreSQL volumes.
- Binary file patterns should be declared in `.gitattributes` where useful.

## Security Requirements

- Ignore private keys, certificates, credentials and common secret files.
- Add a warning that ignoring a file does not remove a secret already committed to Git history.
- No sample value may resemble a real API key or password.

## Acceptance Criteria

- [ ] `git status` is clean after committing the repository foundation.
- [ ] LF normalization is configured.
- [ ] `.env` is ignored and `.env.example` is allowed.
- [ ] Node.js and Python generated files are ignored.
- [ ] Conventional Commits are documented.
- [ ] Recommended branch protection settings are documented.
- [ ] No secrets or restricted data are present.

## Required Tests

### Automated Checks

```bash
git check-ignore .env
printf 'sample' > /tmp/zayd_env_example_check
```

Verify manually that `.env.example` is not ignored.

### Manual Review

- Review all ignore patterns for accidental exclusion of migrations, tasks or documentation.
- Review repository files for secret-like values.

## Documentation Updates

- Root `README.md`
- Commit convention section in `CONTRIBUTING.md` or a dedicated development document

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
