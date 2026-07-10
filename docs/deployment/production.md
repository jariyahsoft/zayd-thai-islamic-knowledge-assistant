# Production deployment reference

This reference targets a multi-node Docker Swarm or an equivalent orchestrator. It is an
architecture and configuration baseline, not production approval. Security, platform, database,
data-license, and Islamic-content owners must review the actual environment before traffic is
enabled. The initial availability target is 99.5%.

## Architecture and failure domains

| Component | Reference topology | Failure-domain requirement |
|---|---|---|
| WAF/load balancer | Managed WAF/LB in front of two `proxy` replicas | Spread across nodes/zones; TLS keys supplied as managed secrets |
| Web | At least two immutable image replicas | Separate nodes/zones; stateless |
| API | At least three replicas, start-first rolling updates | Separate nodes/zones; stateless; no local sessions |
| Workers | Dedicated replicas on backend network | Separate from edge/API placement; queue work must be retryable/idempotent |
| PostgreSQL/pgvector | External managed HA cluster | Multi-zone primary/standby, PITR, tested failover |
| Redis | External managed HA service | Multi-zone replication; cache/queue loss must not corrupt system-of-record data |
| Object storage | External private S3-compatible service | Cross-zone durability, versioning/object lock where required |
| Monitoring | Central Prometheus-compatible service and log platform | Separate operations node/account; restricted operator access |
| Backup | Scheduled `zayd-backup` job plus off-site bucket | Separate account/region and credentials from primary services |

The production Compose file intentionally contains no PostgreSQL, Redis, or MinIO container. Their
connection URLs are external secrets. Local Prometheus and backup staging volumes are declared
external and must use replicated/durable storage or be replaced by managed services.

## Images and secrets

Build, scan, sign, and publish `zayd-web`, `zayd-api`, `zayd-worker`, and `zayd-backup` images from a
reviewed commit. Set `IMAGE_TAG` to an immutable release tag and verify registry digest/signature and
SBOM before deployment. Never deploy `latest`.

Create orchestrator-managed secrets named in `infra/compose/production.yml`, including database and
Redis URLs, S3 credentials, auth secrets, provider credentials, backup encryption key, and TLS
certificate/key. The secret loader fails closed for unreadable or empty files and removes `_FILE`
variables before starting the process. Secret values must not appear in `.env`, Compose config,
logs, CI variables visible to forks, or command history.

Non-secret deployment variables are still required explicitly. Validate without deploying:

```bash
docker compose -f infra/compose/production.yml config --quiet
```

For Swarm, create external configs/secrets/volumes first and deploy with a change-ticketed command:

```bash
docker stack deploy --with-registry-auth --prune \
  --compose-file infra/compose/production.yml zayd
```

Place an environment-specific managed WAF/load balancer in front of ports 80/443. Restrict direct
node access, allow backend egress only to approved state/provider endpoints, and apply node labels
for monitoring and backup placement. The bundled proxy rate limit is a defense-in-depth baseline,
not a replacement for the WAF.

## Probes, monitoring, and failure behavior

- `/health` is process liveness and drives container health checks.
- `/health/dependencies` is a bounded dependency view for readiness/operations; it exposes no URLs
  or credentials. Alert if it remains degraded.
- `/metrics` exports privacy-sanitized in-memory Prometheus metrics. Central monitoring must scrape
  every API replica, retain data outside the application failure domain, and alert on availability,
  error/latency, citation failure, queue depth/age, provider health, and backup failure.
- Worker replicas have no edge/application network. Worker failure must not terminate API replicas;
  retry/dead-letter behavior and queue recovery must be exercised in staging.

If PostgreSQL is unavailable, stop unsafe mutations and follow the managed database failover
procedure. If Redis fails, preserve the PostgreSQL system of record and degrade queue/cache features.
If generation providers fail, preserve local retrieval/read-only behavior. Object-storage failures
must fail closed for upload/publish operations.

## Rolling deployment

1. Confirm backup and restore evidence, migration compatibility, image signatures/SBOM, evaluation
   gates, and security/content approvals.
2. Apply backward-compatible migrations before application rollout.
3. Deploy one API replica at a time. `start-first`, health monitoring, and automatic rollback are
   configured; watch errors, latency, dependency health, citations, and queues for at least one full
   monitor window.
4. Roll workers separately after API stability, then web and proxy. Do not combine stateful failover
   with an application release.

## Canary and rollback

Deploy the candidate tag as a separately named canary stack with one API/web replica and isolated
release labels. Configure the managed LB/WAF—not an application header—to send 1% of eligible,
non-privileged traffic, then 5%, 25%, and 100% only after the defined observation gates. Exclude
admin/reviewer mutations and high-risk religious workflows until explicit reviewers approve them.
Never split traffic between incompatible database schemas or prompt/policy versions.

Rollback traffic immediately for health failures, unsafe/citation regressions, authorization
errors, elevated latency/errors, or queue growth. Redeploy the last signed image tag and restore the
previous LB route. Do not reverse an irreversible migration; use a forward fix or the approved
database/object restore runbook. Preserve incident evidence and invalidate affected answers when
required.

## Backup and recovery

Schedule the `backup-job` profile through the orchestrator at least daily with `replicas=1` for a
single run. It uses separate database/object credentials, encrypts before off-site transfer, and
requires `OFFSITE_S3_URI`. Monitor its exit status and audit file. Perform the documented isolated
restore drill monthly and before release. See `docs/operations/backup-restore.md` and
`docs/operations/disaster-recovery.md`.

## Required production review

Human security and platform review must verify secret-manager integration, TLS/WAF policy, network
rules, image/container scans, host hardening, stateful HA/failover, backup restore evidence,
monitoring alerts, capacity/load results, privacy retention, and incident access. No repository test
can substitute for those environment-specific approvals.
