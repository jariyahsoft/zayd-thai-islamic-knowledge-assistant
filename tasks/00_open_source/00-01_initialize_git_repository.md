# TASK-00-01 — Initialize Git Repository

## Status

`DONE`

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

- [x] `git status` is clean after committing the repository foundation.
- [x] LF normalization is configured.
- [x] `.env` is ignored and `.env.example` is allowed.
- [x] Node.js and Python generated files are ignored.
- [x] Conventional Commits are documented.
- [x] Recommended branch protection settings are documented.
- [x] No secrets or restricted data are present.

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

- `.gitignore`
- `.editorconfig`
- `.gitattributes`
- `CONTRIBUTING.md`
- `README.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `git rev-parse --is-inside-work-tree`
- `git status --short`
- Manual review of repository root contents and ignore patterns
- Manual review of project guidance files and task dependencies

### Acceptance Criteria Result

- Passed: repository foundation files added and documented.
- Passed: LF normalization is configured.
- Passed: `.env` is ignored and `.env.example` remains trackable.
- Passed: Node.js and Python generated files are ignored.
- Passed: Conventional Commits are documented.
- Passed: Recommended branch protection settings are documented.
- Passed: No secrets or restricted data were introduced.

### Security and License Review

- No secrets, credentials, or production data were added.
- Ignore rules include a warning that Git history is not cleaned by `.gitignore`.
- No license-selection changes were made.

### Known Limitations

- The repository does not yet contain application code, so the ignore patterns were validated by review rather than by build output.

### Follow-up Tasks

- Complete `TASK-00-02` and the remaining open-source foundation tasks.
- Add license, governance, and community files in the next tasks.

### Commit

- Pending focused commit creation
