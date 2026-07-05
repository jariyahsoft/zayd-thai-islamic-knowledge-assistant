# Contributing to Zayd

## Repository Baseline

- Use `main` as the default protected branch.
- Keep changes small and focused.
- Never commit secrets, credentials, production data, or restricted religious content.
- Add tests or verification notes for every functional change.

## Branching Model

Recommended branch names:

- `feature/*`
- `fix/*`
- `docs/*`
- `release/*`

Recommended `main` branch protection:

- Require pull requests before merge.
- Disallow direct pushes.
- Disallow force-pushes.
- Disallow branch deletion.
- Require at least one approving review.
- Dismiss stale approvals after new commits.
- Require status checks to pass before merge.
- Require conversation resolution before merge.
- Prefer squash merges for a clean history.

## Conventional Commits

Use Conventional Commits for all repository changes.

Required prefixes:

- `feat`
- `fix`
- `docs`
- `refactor`
- `test`
- `chore`
- `build`
- `ci`
- `security`

Examples:

```text
feat(api): add health endpoint
docs: describe protected branch settings
security(repo): ignore local secret files
```

## Commit Hygiene

- Keep each commit focused on a single task or logical change.
- Mention the intent of the change in the subject line.
- Avoid mixing unrelated refactors with feature work.
- Use the body to note verification when it adds value.

## Secret Handling

- Store real secrets outside the repository.
- Keep `.env.example` free of real credentials.
- Remember that `.gitignore` prevents new tracking but does not remove old secrets from Git history.

## License and Provenance

- Treat source-code, documentation, trademark, and dataset rights as separate.
- Record imported or adapted third-party code in `CODE_PROVENANCE.md` before merge.
- Add attribution requirements to `THIRD_PARTY_NOTICES.md` when applicable.
- Keep dataset redistribution denied by default unless a dataset manifest
  explicitly allows it.
- Require human license review before merging third-party code, third-party
  documentation assets, or redistributable sample data.
