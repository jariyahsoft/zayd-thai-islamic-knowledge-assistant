# Development Docker

## Quick Start

1. Copy `.env.example` to `.env` if you want to override defaults later.
2. Start the stack:

```bash
docker compose up -d
```

The default host ports are:

- `3100` -> web
- `3101` -> reviewer
- `3102` -> admin
- `8000` -> API

3. Stop the stack:

```bash
docker compose down
```

4. Reset development volumes:

```bash
docker compose down -v
```

## Stack Contents

- PostgreSQL with pgvector
- Redis
- MinIO with a private development bucket
- API
- Worker
- Web
- Reviewer
- Admin

## Notes

- PostgreSQL, Redis, and MinIO are only reachable on the internal Compose network by default.
- Frontend host ports default to `3100`-`3102` to avoid common local conflicts on `3000`-`3002`.
- Development credentials are placeholders only and must not be reused in production.
- Health checks use internal service names and do not expose secrets.
- Configuration validation details are documented in [`docs/development/configuration.md`](../development/configuration.md).
