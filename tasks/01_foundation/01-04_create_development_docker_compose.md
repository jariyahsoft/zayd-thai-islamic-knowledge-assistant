# TASK-01-04 — Create Development Docker Compose

## Status

`TODO`

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

- [ ] `docker compose config` succeeds.
- [ ] `docker compose up -d` starts all defined services.
- [ ] All service health checks become healthy.
- [ ] PostgreSQL confirms the vector extension is available.
- [ ] MinIO object storage can create and read a private test object.
- [ ] API can reach PostgreSQL, Redis and MinIO through internal networking.
- [ ] No proprietary service or cloud key is required.
- [ ] No infrastructure database is publicly exposed by default.

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
