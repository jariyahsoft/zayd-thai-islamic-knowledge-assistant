# Closed pilot environment

The pilot is a separate deployment from production. It has its own database, Redis, object-storage
bucket/account, managed secrets, backup destination, monitoring volume, image tag, invite allowlist,
and approved dataset manifest. Do not clone production data, credentials, user identities, object
keys, or provider logs into the pilot.

## Preconditions

Before deployment, the release owner must obtain and record:

1. A human scholar/data-license approval ID for the selected dataset manifest.
2. Its SHA-256 checksum and storage location in the isolated pilot environment.
3. Security/platform approval for the pilot secret namespace, TLS/WAF, network rules, backup target,
   monitoring/alert routing, and named participant process.
4. A release-candidate image tag, SBOM/signature evidence, migration plan, and restore-drill evidence.

The repository does not contain participant details or an approved pilot dataset. Those are
environment-owned records.

## Isolation and deployment gate

Export non-secret values from the approved deployment system, then validate before creating a stack:

```bash
bash infra/scripts/validate-pilot-environment.sh
docker compose -f infra/compose/production.yml -f infra/compose/pilot.yml config --quiet
```

The validator fails unless every secret is a distinct `pilot-*` name, the dataset manifest is
readable, its checksum matches, and a human approval ID is supplied. Deploy through a change ticket
only after the gate passes:

```bash
docker stack deploy --with-registry-auth --prune \
  --compose-file infra/compose/production.yml \
  --compose-file infra/compose/pilot.yml zayd-pilot
```

Use a distinct cloud account/project where possible. Deny production-to-pilot network paths and use
separate provider project/API credentials. Do not publish pilot object storage or Prometheus outside
the operations boundary.

## Invite-only access

Set `PILOT_MODE=true` through the pilot overlay. It disables guest sessions and requires an
orchestrator secret containing comma-separated SHA-256 hashes of normalized participant emails.
The raw invite list is never committed or returned by the API. Registration succeeds only for a
matching hash; success and denial produce audit records without recording the email/hash in the
audit payload. Administrators must issue, expire, and revoke invite hashes through the approved
participant register and review audit logs regularly.

## Operational checks

Before inviting users, confirm `/health/dependencies`, central metrics/alerts, and the daily
encrypted backup job. Run an isolated restore drill using pilot targets, then test an invited account
registration/login, a denied registration, RBAC/MFA for privileged users, document visibility, and
feedback/incident flow. Record results, trace IDs, date, owner, release tag, dataset approval ID,
and any exceptions in the release gate.

Stop new registrations and pilot traffic for a P0/P1 incident, suspected data crossover, missing
backup, degraded dependency health, unauthorized access, unsafe answer, or license/scholar-review
concern. Preserve audit evidence and follow the incident and restore runbooks.
