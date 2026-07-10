DROP TRIGGER IF EXISTS trg_incident_events_immutable ON incident_events;
DROP FUNCTION IF EXISTS zayd_reject_incident_event_mutation();
DROP TABLE IF EXISTS incident_events;
DROP INDEX IF EXISTS idx_incidents_owner_status;
DROP INDEX IF EXISTS uq_incidents_idempotency_key;
ALTER TABLE incidents
  DROP COLUMN IF EXISTS row_version,
  DROP COLUMN IF EXISTS policy_version,
  DROP COLUMN IF EXISTS alert_status,
  DROP COLUMN IF EXISTS idempotency_key,
  DROP COLUMN IF EXISTS owner_id;
