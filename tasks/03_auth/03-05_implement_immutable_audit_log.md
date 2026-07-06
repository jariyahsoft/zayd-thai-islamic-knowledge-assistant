# TASK-03-05 — Implement Immutable Audit Log

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §35 Observability
- NFR-SEC-011
- FR-ADM-012

## Objective

Create append-only audit records for sensitive authentication, authorization, document, review, publication, provider, prompt and policy actions.

## Scope

### In Scope

- Create append-only audit records for sensitive authentication, authorization, document, review, publication, provider, prompt and policy actions.
- Add querying and export for authorized auditors.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-03

## Expected Files

- Implementation files under the relevant `03_auth` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use server-side enforcement and least privilege.
- Do not log credentials, tokens or sensitive recovery material.
- Return stable, non-enumerating error responses.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Apply OWASP authentication/session guidance and rate limiting.

## Acceptance Criteria

- [x] Application roles cannot update or delete audit entries.
- [x] Records include actor, action, resource, timestamp, request ID and safe before/after summaries.
- [x] Secrets and unnecessary personal data are redacted.
- [x] Tamper-evidence or external archival strategy is documented.

## Required Tests

### Unit and Contract Tests

- Audit coverage tests
- Mutation-denial tests
- Redaction tests
- Export authorization tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/security/audit-logging.md`
- `docs/operations/audit-retention.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/audit.py` — audit query/export service, serialization, bounded filters, and NDJSON export.
- `services/common/src/zayd_common/database/models.py` — audit log request ID, hash-chain fields, redaction, content hashing, and ORM append-only update/delete guards.
- `services/common/src/zayd_common/rbac.py` — `audit.verify` permission plus admin/auditor audit export coverage.
- `services/common/src/zayd_common/auth.py` — request ID propagation for auth audit records.
- `services/common/src/zayd_common/mfa.py` — request ID propagation for MFA audit records.
- `services/common/src/zayd_common/guest.py` — request ID propagation for guest-session audit records and formatting.
- `services/common/src/zayd_common/database/__init__.py` and `services/common/src/zayd_common/__init__.py` — audit exports.
- `services/api/src/zayd_service_api/app.py` — protected audit list and NDJSON export endpoints.
- `database/migrations/0006_immutable_audit_logs.up.sql` and `database/migrations/0006_immutable_audit_logs.down.sql` — database-level request ID, reason compatibility, hash-chain fields, indexes, append-only triggers, and development/test rollback.
- `database/migrations/README.md` — migration registry update.
- `services/common/tests/test_audit.py` — audit chaining, mutation-denial, redaction, export, and query tests.
- `services/api/tests/test_audit_api.py` — audit read/export authorization and auditor read-only tests.
- `docs/security/audit-logging.md` — immutable audit logging model, redaction, tamper evidence, and endpoint docs.
- `docs/operations/audit-retention.md` — retention, external archival, access-control, and restore guidance.
- `tasks/03_auth/03-05_implement_immutable_audit_log.md`, `tasks/00_task_index.md`, and `tasks-update.md` — task tracking updates.

### Commands and Tests Executed

```bash
uv run pytest services/common/tests/test_audit.py services/api/tests/test_audit_api.py
uv run ruff check services/common/src/zayd_common/audit.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/rbac.py services/common/src/zayd_common/auth.py services/common/src/zayd_common/mfa.py services/common/src/zayd_common/guest.py services/common/src/zayd_common/database/__init__.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_audit.py services/api/tests/test_audit_api.py
uv run mypy services/common/src/zayd_common/audit.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/rbac.py services/common/src/zayd_common/auth.py services/common/src/zayd_common/mfa.py services/common/src/zayd_common/guest.py services/api/src/zayd_service_api/app.py
uv run ruff format --check services/common/src/zayd_common/audit.py services/common/src/zayd_common/database/models.py services/common/src/zayd_common/rbac.py services/common/src/zayd_common/auth.py services/common/src/zayd_common/mfa.py services/common/src/zayd_common/guest.py services/common/src/zayd_common/database/__init__.py services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py services/common/tests/test_audit.py services/api/tests/test_audit_api.py
uv run pytest services/common/tests/test_audit.py services/api/tests/test_audit_api.py services/common/tests/test_rbac.py services/api/tests/test_rbac_api.py services/common/tests/test_auth.py services/common/tests/test_mfa.py services/common/tests/test_guest.py
MIGRATION_ACTION=up make migrate
uv run pytest
uv run ruff check .
uv run pytest database/tests/test_initial_migration.py
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U zayd_dev -d zayd_dev <<'SQL'
INSERT INTO audit_logs (action, resource_type, outcome, request_id, trace_id, source_context)
VALUES ('audit.verify.insert', 'audit', 'success', 'req-audit-smoke', 'trace-audit-smoke', '{}'::jsonb)
RETURNING hash_algorithm, previous_hash IS NOT NULL AS has_previous_hash, length(content_hash) AS hash_length;
DO $$
DECLARE
  audit_id uuid;
BEGIN
  SELECT id INTO audit_id FROM audit_logs WHERE request_id = 'req-audit-smoke' LIMIT 1;
  BEGIN
    UPDATE audit_logs SET outcome = 'error' WHERE id = audit_id;
    RAISE EXCEPTION 'audit update unexpectedly succeeded';
  EXCEPTION WHEN OTHERS THEN
    IF SQLERRM = 'audit update unexpectedly succeeded' THEN
      RAISE;
    END IF;
  END;
END $$;
SQL
```

Results:
- Focused audit tests passed: 9 tests.
- Focused auth/RBAC/MFA/guest audit regression suite passed: 50 tests.
- Focused `ruff check`, `ruff format --check`, and `mypy` passed after formatting `services/common/src/zayd_common/guest.py`.
- `MIGRATION_ACTION=up make migrate` applied `0006_immutable_audit_logs` successfully.
- Full `uv run pytest` passed: 128 tests.
- `uv run pytest database/tests/test_initial_migration.py` passed: 4 tests.
- PostgreSQL smoke test inserted a hash-chained audit row and confirmed database-level update denial.
- `uv run ruff check .` still reports one pre-existing line-length issue in `services/common/src/zayd_common/settings.py:112`, outside the TASK-03-05 change set.

### Acceptance Criteria Result

- [x] Application roles cannot update or delete audit entries: no application role has audit mutation permission; ORM update/delete operations raise; PostgreSQL triggers reject `UPDATE` and `DELETE` on `audit_logs`.
- [x] Records include actor, action, resource, timestamp, request ID and safe before/after summaries: model/service/API now expose these fields and existing auth/RBAC/MFA/guest audit helpers propagate request ID from trace/request metadata.
- [x] Secrets and unnecessary personal data are redacted: audit summaries and source context redact sensitive keys before hashing and persistence; tests cover nested token/password/authorization redaction.
- [x] Tamper-evidence or external archival strategy is documented: audit rows are SHA-256 hash chained and docs describe external object-lock/SIEM archival and checkpointing.

### Security and License Review

- Audit endpoints enforce server-side RBAC: `audit.read` for list and `audit.export` for NDJSON export.
- Auditors remain read-only and cannot use role mutation endpoints.
- Admin export now requires MFA through the existing privileged-access dependency.
- Audit content is minimized to summaries and metadata; no credentials, Telegram values, production data, restricted religious content, hidden reasoning, third-party code, or new dependencies were introduced.
- Hash chaining is tamper-evident, not tamper-proof against database superusers; operational docs require external archival/checkpoints for production.

### Known Limitations

- External write-once storage, SIEM forwarding, and automated retention jobs are documented but deferred to later operations tasks.
- Existing historical audit rows are hash-filled by migration, but old rows may have lacked request IDs or reasons before this task.
- Direct database superusers can still bypass application controls; production must restrict superuser access and archive checkpoints externally.
- `uv run ruff check .` has an unrelated pre-existing failure in `services/common/src/zayd_common/settings.py:112`.

### Follow-up Tasks

- TASK-04-01 and later source/license/document/review/provider/prompt/policy services must call `AuditService.record(...)` for sensitive mutations.
- EPIC-13 operations tasks should implement scheduled audit export, object-lock storage/SIEM integration, and formal retention enforcement.

### Commit

- Not created in this run because the active runtime policy requires an explicit user request before committing.
