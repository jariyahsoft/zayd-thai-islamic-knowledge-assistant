ALTER TABLE incidents
  ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS idempotency_key text,
  ADD COLUMN IF NOT EXISTS alert_status text NOT NULL DEFAULT 'not_required',
  ADD COLUMN IF NOT EXISTS policy_version text NOT NULL DEFAULT 'incident-management-v1',
  ADD COLUMN IF NOT EXISTS row_version integer NOT NULL DEFAULT 1;

UPDATE incidents SET idempotency_key = 'legacy:' || id::text WHERE idempotency_key IS NULL;
ALTER TABLE incidents ALTER COLUMN idempotency_key SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_incidents_idempotency_key ON incidents (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_incidents_owner_status ON incidents (owner_id, status, created_at);

CREATE TABLE IF NOT EXISTS incident_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  incident_id uuid NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  actor_user_id uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  status_from text,
  status_to text,
  details_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  request_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incident_events_timeline ON incident_events (incident_id, created_at, id);

CREATE OR REPLACE FUNCTION zayd_reject_incident_event_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'incident_events are append-only'; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_incident_events_immutable ON incident_events;
CREATE TRIGGER trg_incident_events_immutable BEFORE UPDATE OR DELETE ON incident_events
FOR EACH ROW EXECUTE FUNCTION zayd_reject_incident_event_mutation();
