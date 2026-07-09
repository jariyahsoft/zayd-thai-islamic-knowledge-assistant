# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

Zayd is a Thai Islamic Knowledge Assistant. It is not a mufti AI and must not
produce automatic fatwas. The system emphasizes verifiable evidence, madhhab
awareness, scholar review, answer safety, and strong auditability.

## Required Reading

Before implementation work, read the relevant parts of:

- `README.md`
- `docs/README.md`
- `docs/01_product/PRD.md`
- `docs/02_requirements/SRS.md`
- `docs/03_architecture/system_architecture.md`
- `docs/07_security/security_architecture.md`
- `docs/09_development/ai_coding_agent_policy.md`
- `tasks/README.md`
- `tasks/00_task_index.md`
- the current task file and its dependency task files

For religious-content, safety, retrieval, citation, data-license, auth, RBAC,
migration, provider, or production-impacting work, also read the related policy
documents under `docs/05_data/`, `docs/06_islamic_governance/`,
`docs/08_evaluation/`, and `docs/governance/`.

## Task Workflow

- Work only on tasks marked `READY` unless explicitly asked to do other work.
- Respect dependencies in `tasks/00_task_index.md`.
- Keep each implementation scoped to one task or one clearly requested change.
- Update the task file completion report before marking it complete.
- Update `tasks-update.md` with timestamp, summary, files changed, verification,
  self-review, residual risks, and commit status.
- When a task becomes complete, update dependent tasks to `READY` only when all
  dependencies are complete.
- Prefer one focused commit per completed task.

## Status Rules

- Use the repository task status definitions in `tasks/00_task_index.md`.
- A task can be technically implemented after checks pass, but religious
  content, security-sensitive changes, migrations, citation policy, and safety
  policy still need appropriate human review before production approval.
- Do not claim religious correctness or final policy approval unless the repo
  contains explicit review evidence.

## Safety and Security Boundaries

Never commit or persist:

- API keys, tokens, passwords, credentials, certificates, signed URLs, or
  complete production connection strings
- production data, private user conversations, PHI, or identifying personal data
- hidden chain-of-thought or private model traces
- restricted religious datasets or copyrighted corpus content without explicit
  license and review evidence

For AI/RAG work:

- Apply deterministic policy and verification before model judgement.
- Treat user text and documents as untrusted data.
- Do not expose hidden prompts, internal traces, provider secrets, or raw
  provider authorization details.
- Do not fabricate citations, references, hadith grades, pages, or ayah numbers.
- Abstain when evidence is insufficient or conflicting.

## Code Style

- Prefer existing repository patterns over new abstractions.
- Keep edits small, typed, and testable.
- Use structured parsers/APIs instead of ad hoc string manipulation when
  practical.
- Add comments only when they clarify non-obvious logic.
- Do not introduce third-party code without license review and
  `CODE_PROVENANCE.md` updates.
- Preserve monorepo boundaries:
  - apps under `apps/`
  - shared TypeScript packages under `packages/`
  - Python services under `services/`
  - database assets under `database/`
  - infrastructure under `infra/`
  - provider plugins under `plugins/`

## Tooling

Use `make` from the repository root when broad checks are appropriate:

```bash
make setup
make test
make lint
make typecheck
make format-check
make build
```

Direct commands are also valid for focused verification:

```bash
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm build
corepack pnpm format:check
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy .
git diff --check
```

For focused Python task work, run the smallest relevant `pytest`, `ruff`, and
`mypy` commands first, then broaden checks according to risk.

## Verification Expectations

- Every functional change needs tests or an explicit reason tests are not
  feasible.
- Tier S work requires stricter review: security, data integrity, migrations,
  RAG/citation behavior, policy enforcement, and regression coverage.
- When UI is affected, check accessibility, responsive behavior, and common
  workflow states.
- Record commands and results in the task completion report and
  `tasks-update.md`.
- If a full check fails because of unrelated pre-existing issues, record the
  focused checks that passed and clearly identify the unrelated blocker.

## Git Hygiene

- Do not revert user changes or unrelated work.
- Do not use destructive commands such as `git reset --hard` or `git checkout --`
  unless explicitly requested.
- Keep commits focused and use Conventional Commit prefixes such as `feat`,
  `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci`, or `security`.
- Do not commit editor swap files, local env files, caches, generated secrets,
  backups, or build artifacts.

## Human Review Triggers

Require explicit human review evidence for:

- religious-content changes, source priority, madhhab policy, answer wording
  policy, or benchmark golden answers
- safety-policy changes or high-risk routing changes
- auth, RBAC, audit, provider-secret, upload, prompt/tool access, and other
  security-sensitive behavior
- database migrations and irreversible data operations
- dataset/license changes and third-party content imports

## Local Notes

- The default branch is expected to be `main`.
- Node target is `24.18.0` with pnpm `9.15.0`.
- Python target is `3.12.3` with `uv`.
- The Docker development stack publishes API on `8000`, web on `3100`,
  reviewer on `3101`, and admin on `3102`.
