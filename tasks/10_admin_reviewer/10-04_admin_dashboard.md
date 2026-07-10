# TASK-10-04 — Admin Dashboard

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-ADM-008
- FR-ADM-012

## Objective

Display system/provider health, queue depth, user counts, RAG hit rate, cost summary and incidents.

## Scope

### In Scope

- Display system/provider health, queue depth, user counts, RAG hit rate, cost summary and incidents.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-13-03

## Expected Files

- Implementation files under the relevant `10_admin_reviewer` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Server-side RBAC is authoritative.
- Protect sensitive source, reviewer and operational information.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Use least privilege for reviewer/admin data.

## Acceptance Criteria

- [x] Metrics are access controlled and time-bounded.
- [x] Dashboard handles missing telemetry gracefully.
- [x] No secrets or raw private conversation data are shown.

## Required Tests

### Unit and Contract Tests

- Dashboard API/component tests
- RBAC tests
- Telemetry outage tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/user/admin-dashboard.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/api/src/zayd_service_api/app.py` — replaced the public metrics snapshot with the RBAC/MFA-protected `GET /admin/dashboard` aggregate endpoint, bounded `window_minutes`, user and incident counts, and no raw Prometheus response.
- `services/api/tests/test_metrics_api.py` — added unauthenticated, unauthorized, and authorized dashboard contract coverage with bounded-window and aggregate-privacy assertions.
- `apps/admin/app/admin-dashboard.tsx` — added the accessible admin dashboard with in-memory token handling, bounded window selection, aggregate cards, and telemetry-unavailable state.
- `apps/admin/app/admin-data.ts` — added the typed dashboard API contract and request helper.
- `apps/admin/app/workspace.tsx` — added Dashboard as the default admin section.
- `docs/user/admin-dashboard.md` — documented access controls, privacy boundaries, indicators, and outage behavior.
- `docs/operations/metrics.md`, `infra/monitoring/README.md`, and `infra/monitoring/prometheus.yml` — removed the now-invalid public scrape guidance pending a protected Prometheus-compatible endpoint.
- `tasks/00_task_index.md` and `tasks-update.md` — recorded task completion.

### Commands and Tests Executed

- `uv run pytest services/api/tests/test_metrics_api.py -q` — passed (1 passed).
- `uv run ruff check services/api/src/zayd_service_api/app.py services/api/tests/test_metrics_api.py` — passed.
- `uv run mypy services/api/src/zayd_service_api/app.py --ignore-missing-imports` — passed.
- `git diff --check` — passed.
- Admin frontend test/typecheck/build could not run because `node` and `corepack` are unavailable in this environment.

### Acceptance Criteria Result

- Passed. Dashboard data is available only through `/admin/dashboard`, protected by server-side `audit.read` RBAC and privileged MFA; `window_minutes` is constrained to 1–1440.
- Passed. The UI clears prior dashboard values and presents an alert when the protected telemetry request fails.
- Passed. The contract exposes aggregate counts and configured cost limits only; raw telemetry export, conversation text, source content, signed URLs, and provider secrets are excluded.

### Security and License Review

- No secrets, production data, restricted religious content, or third-party code were introduced.
- The former public metrics response was removed in favor of a least-privilege read-only dashboard endpoint. Server-side RBAC and MFA remain authoritative.
- Incident totals are derived from audit metadata only; no incident bodies or audit-log details are returned.

### Known Limitations

- Repository-stage telemetry is process-local and not durable; the bounded request window is not a substitute for production time-series retention.
- Frontend runtime/build validation requires a Node-enabled environment.

### Follow-up Tasks

- Production operations work should back the dashboard with a durable telemetry store and retained time-series queries.

### Commit

- Pending.
