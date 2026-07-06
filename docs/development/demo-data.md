# Demo Data

The demo dataset is synthetic and intended only for local development, QA, and verification.

## Goals

- Provide repeatable seed data for demo users, roles, sources, licenses, documents, citations, feedback, and incidents.
- Keep all content visibly labeled as non-authoritative.
- Avoid private, copyrighted, or restricted religious corpora.

## Command

Run the seed command from the repository root:

```bash
make seed-demo
```

The command uses `database/seeds/seed.py` and is idempotent. Running it twice should not create duplicate rows.

## Generated Credentials

The first run creates temporary demo user passwords and prints them once.

- Treat the printed passwords as rotation-required.
- Do not reuse them for production or long-lived accounts.
- Re-run the command only if you want to verify idempotency or refresh a local demo environment.

## Data Labels

Demo source and document names include `[DEMO - NON-AUTHORITATIVE]` so that the data is visibly distinguishable from approved content.

## Verification

Recommended checks:

```bash
make seed-demo
make seed-demo
uv run pytest services/common/tests/test_seeding.py
```

If you are targeting a custom database, set `DATABASE_URL` before running `make seed-demo`.
