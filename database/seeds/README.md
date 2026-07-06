# Database Seeds

Owner category: database and QA maintainers.

Seed assets must contain only synthetic, public-domain, or explicitly redistributable sample data.

## Demo Seed Command

Use `make seed-demo` from the repository root to load the demo dataset through `database/seeds/seed.py`.

The seed command is designed to be:

- Idempotent: repeated runs do not create duplicate rows.
- Non-authoritative: demo source and document labels visibly include `[DEMO - NON-AUTHORITATIVE]`.
- Rotation-safe: the first run generates temporary demo credentials and prints them once.

Recommended workflow:

```bash
make seed-demo
make seed-demo
```

If you are using a non-default database connection, set `DATABASE_URL` before running the command.
