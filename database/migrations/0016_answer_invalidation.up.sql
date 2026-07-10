CREATE TABLE IF NOT EXISTS answer_invalidations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  answer_id uuid NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
  incident_id uuid REFERENCES incidents(id) ON DELETE SET NULL,
  citation_id uuid REFERENCES citations(id) ON DELETE SET NULL,
  source_id uuid REFERENCES sources(id) ON DELETE SET NULL,
  reason text NOT NULL,
  warning text NOT NULL,
  actor_user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  idempotency_key text NOT NULL UNIQUE,
  notification_status text NOT NULL,
  policy_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_answer_invalidations_answer ON answer_invalidations (answer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_answer_invalidations_incident ON answer_invalidations (incident_id, created_at);

CREATE OR REPLACE FUNCTION zayd_reject_answer_invalidation_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'answer_invalidations are append-only'; END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_answer_invalidations_immutable ON answer_invalidations;
CREATE TRIGGER trg_answer_invalidations_immutable BEFORE UPDATE OR DELETE ON answer_invalidations
FOR EACH ROW EXECUTE FUNCTION zayd_reject_answer_invalidation_mutation();
