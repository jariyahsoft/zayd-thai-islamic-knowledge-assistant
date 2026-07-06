# TASK-01-04 — Create Development Docker Compose

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-OSS-002 — Development Docker Compose
- FR-OSS-003 — Minimal self-host Docker Compose
- FR-OSS-004 — No proprietary dependency required
- SRS §43 Self-host Deployment Profiles
- SRS §33 Availability Requirements

## Objective

Create a reproducible local development stack that starts Zayd's foundational applications and infrastructure without requiring any proprietary cloud service.

## Scope

### In Scope

Add Dockerfiles and Compose configuration for:

- PostgreSQL with pgvector
- Redis
- MinIO
- API service
- Worker service
- User web application
- Reviewer application
- Admin application

Also include:

- Named volumes
- Internal networks
- Health checks
- Development-friendly bind mounts where appropriate
- Dependency ordering based on health, not only container start

### Out of Scope

- Production hardening.
- Kubernetes.
- Real LLM or embedding deployment.
- Nginx/Traefik production routing.
- Monitoring stack.

## Dependencies

- TASK-01-02
- TASK-01-03

## Expected Files

```text
docker-compose.yml
compose.dev.yml or infra/compose/development.yml
infra/docker/*
apps/*/Dockerfile
services/*/Dockerfile
```

## Functional Requirements

1. `docker compose up -d` must start the foundational stack.
2. PostgreSQL must include the pgvector extension.
3. MinIO must use private buckets by default.
4. API and application health checks must be available.
5. Services must use internal service names instead of host-specific addresses.
6. The stack must start with placeholder local configuration and no proprietary API keys.

## Technical Requirements

- Use non-root users in application containers where practical.
- Use multi-stage builds where useful.
- Pin image major/minor versions rather than floating `latest` tags.
- Add persistent volumes for PostgreSQL, Redis and MinIO development data.
- Provide a clean reset command or documented volume-removal procedure.
- Avoid sharing Docker socket with application containers.

## Security Requirements

- Do not expose PostgreSQL, Redis or MinIO publicly by default.
- Development credentials must be clearly marked as non-production.
- Do not commit generated MinIO access keys beyond placeholder development defaults.
- Containers must not run privileged.
- Health endpoints must not include secrets.

## Acceptance Criteria

- [x] `docker compose config` succeeds.
- [x] `docker compose up -d` starts all defined services.
- [x] All service health checks become healthy.
- [x] PostgreSQL confirms the vector extension is available.
- [x] MinIO object storage can create and read a private test object.
- [x] API can reach PostgreSQL, Redis and MinIO through internal networking.
- [x] No proprietary service or cloud key is required.
- [x] No infrastructure database is publicly exposed by default.

## Required Tests

### Integration Tests

- Database connection and pgvector extension check.
- Redis ping.
- MinIO bucket/object round trip.
- API health endpoint.
- Frontend health/root response.

### Security Checks

- Inspect container users.
- Inspect published ports.
- Confirm no privileged containers.

## Documentation Updates

- `docs/development/docker.md`
- Root quick-start section

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `.dockerignore`
- `.env.example`
- `docker-compose.yml`
- `infra/compose/development.yml`
- `infra/docker/postgres/Dockerfile`
- `infra/scripts/minio-bootstrap.sh`
- `services/api/Dockerfile`
- `services/api/pyproject.toml`
- `services/worker/Dockerfile`
- `services/worker/src/zayd_service_worker/main.py`
- `apps/web/Dockerfile`
- `apps/reviewer/Dockerfile`
- `apps/admin/Dockerfile`
- `docs/development/docker.md`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `tasks/00_task_index.md`
- `tasks/01_foundation/01-04_create_development_docker_compose.md`
- `tasks-update.md`

### Commands and Tests Executed

- `docker compose config`
- `sh -n infra/scripts/minio-bootstrap.sh`
- `docker compose up -d`
- `docker compose up -d --build api worker`
- `docker compose up -d web reviewer admin`
- `docker compose ps`
- `docker compose logs --no-color --tail=120 web reviewer admin`
- `docker compose exec -T postgres psql -U zayd_dev -d zayd_dev -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname FROM pg_extension WHERE extname = 'vector';"`
- `docker compose exec -T redis redis-cli ping`
- `docker run --rm --entrypoint /bin/sh --network zayd-thai-islamic-knowledge-assistant_internal -e MC_HOST_zayd=http://minioadmin:minioadmin@minio:9000 minio/mc:RELEASE.2025-08-13T08-35-41Z -lc "printf 'compose-check' >/tmp/check.txt && mc cp /tmp/check.txt zayd/zayd-private/task-01-04-check.txt >/dev/null && mc cat zayd/zayd-private/task-01-04-check.txt"`
- `docker compose exec -T api python -c "import socket, urllib.request; socket.create_connection(('postgres', 5432), timeout=5).close(); socket.create_connection(('redis', 6379), timeout=5).close(); urllib.request.urlopen('http://minio:9000/minio/health/live', timeout=5).read(); print('api-dependencies-ok')"`
- `curl --silent --show-error --fail http://localhost:8000/health`
- `curl --silent --show-error --fail http://localhost:3100`
- `curl --silent --show-error --fail http://localhost:3101`
- `curl --silent --show-error --fail http://localhost:3102`
- `docker inspect zayd-thai-islamic-knowledge-assistant-api-1 zayd-thai-islamic-knowledge-assistant-worker-1 zayd-thai-islamic-knowledge-assistant-web-1 zayd-thai-islamic-knowledge-assistant-reviewer-1 zayd-thai-islamic-knowledge-assistant-admin-1 --format '{{.Name}} user={{.Config.User}} privileged={{.HostConfig.Privileged}}'`
- `docker inspect zayd-thai-islamic-knowledge-assistant-postgres-1 zayd-thai-islamic-knowledge-assistant-redis-1 zayd-thai-islamic-knowledge-assistant-minio-1 --format '{{.Name}} ports={{json .NetworkSettings.Ports}} privileged={{.HostConfig.Privileged}}'`

### Acceptance Criteria Result

- Passed. The development stack starts from the root Compose entrypoint, all defined services reached healthy status, `pgvector` is enabled, MinIO private bucket round-trip succeeded, the API reached PostgreSQL/Redis/MinIO across the internal network, no proprietary credentials were required, and PostgreSQL/Redis/MinIO remained unexposed on host ports.

### Security and License Review

- Reviewed for task scope. Development credentials remain placeholder-only, application containers run as non-root users where practical (`appuser` and `node`), no containers run privileged, Docker socket is not mounted, and no new third-party source code was vendored. Pinned image or tool versions were used instead of `latest`.

### Known Limitations

- Frontend host ports default to `3100`-`3102` instead of `3000`-`3002` to avoid common local conflicts while preserving internal container ports.
- The worker is a long-lived placeholder process for Compose health verification and does not yet execute real background jobs.
- The stack is development-focused and intentionally omits production hardening, ingress, and observability components.

### Follow-up Tasks

- `TASK-01-05` should validate environment configuration and document any required `.env` overrides for local operators.
- Future infrastructure tasks can extend this baseline with self-host and production deployment profiles without changing the foundational service topology.

### Commit

- Not created in this task attempt.
