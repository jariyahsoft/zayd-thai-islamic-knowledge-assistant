# Incident Management

Zayd records incidents at severity `P0`, `P1`, `P2`, or `P3`. Incidents move through the governed
states `open → triaged → mitigated → resolved → closed`; invalid transitions and stale row versions
are rejected. Reopening a closed incident is supported by the existing state policy.

Every creation, assignment, and state transition adds an append-only timeline event and a
hash-chained audit record. Creation requires an idempotency key, so a retried request does not send
another alert or create another incident. P0/P1 incidents invoke the configured `IncidentAlertSink`;
deployments must configure an operations-owned sink before production. Alert messages contain only
the incident ID, severity, and minimized summary.

Incidents may link to feedback, an answer, a citation, and a document. Document suspension remains
behind the existing senior-scholar/admin lifecycle endpoint, and answer invalidation is handled by
TASK-11-04. Exports are capped at 200 rows and omit reporter identifiers, feedback bodies,
conversation text, and affected-content identifiers.

Protected API routes:

- `POST /admin/incidents`
- `POST /admin/incidents/{incident_id}/transition`
- `PUT /admin/incidents/{incident_id}/owner`
- `GET /admin/incidents/{incident_id}/timeline`
