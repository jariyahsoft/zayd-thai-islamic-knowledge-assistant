# Configuration

## Principles

- Copy `.env.example` to `.env` for local development.
- Keep browser-safe values in `NEXT_PUBLIC_*` variables only.
- Never commit real secrets, provider credentials, or production endpoints.
- Startup validation must fail fast with concise messages that name invalid variables without printing their values.

## Root Variables

### Application

- `APP_ENV`: `local`, `development`, `test`, or `production`
- `APP_URL`: primary local application URL
- `WEB_PORT`, `REVIEWER_PORT`, `ADMIN_PORT`: host port overrides for local Compose
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, or `ERROR`

### Data and Storage

- `DATABASE_URL`
- `REDIS_URL`
- `S3_ENDPOINT`
- `S3_REGION`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`

### Authentication

- `AUTH_JWT_SECRET`
- `AUTH_SESSION_SECRET`

### LLM and Embeddings

- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `PROVIDER_TOKEN`

### Product Defaults and Feature Flags

- `DEFAULT_LANGUAGE`
- `DEFAULT_MADHHAB`
- `ENABLE_EXTERNAL_PROVIDERS`
- `ENABLE_GUEST_MODE`

## Frontend Variables

Only the following value is intended for browser bundles in the current foundation stage:

- `NEXT_PUBLIC_API_BASE_URL`

Do not expose database URLs, storage secrets, auth secrets, or provider tokens through `NEXT_PUBLIC_*`.

## Validation Rules

- Required URLs must be absolute and valid.
- Booleans must be exactly `true` or `false`.
- Providers must match built-in allowlists unless a future plugin registration layer expands them.
- `ENABLE_EXTERNAL_PROVIDERS=false` enforces a local-only profile.
- Production mode rejects known development placeholder secrets.
- Secret values remain redacted in Python representations and are not included in validation error output.

## Local Development

```bash
cp .env.example .env
docker compose up -d
```

The default development profile publishes:

- `http://localhost:3100` for web
- `http://localhost:3101` for reviewer
- `http://localhost:3102` for admin
- `http://localhost:8000` for API

## Validation Checks

- TypeScript config package tests verify required public values, URL parsing, provider validation, and production secret rejection.
- Python shared settings tests verify missing-value failures, invalid URLs, invalid providers, secret redaction, and production-mode safeguards.
- Frontend validation must keep server-only values out of bundles; use `scripts/check-frontend-env-leaks.sh` after a build when validating bundle output.
