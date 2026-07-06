-- TASK-03-05 — Roll back immutable audit log hardening
-- Development/test rollback only. Removes hash-chain columns and restores updated_at trigger behavior.

BEGIN;

DROP TRIGGER IF EXISTS trg_audit_logs_no_delete ON audit_logs;
DROP TRIGGER IF EXISTS trg_audit_logs_no_update ON audit_logs;
DROP TRIGGER IF EXISTS trg_audit_logs_set_hash ON audit_logs;

DROP INDEX IF EXISTS idx_audit_logs_hash_chain;
DROP INDEX IF EXISTS idx_audit_logs_request;
DROP INDEX IF EXISTS uq_audit_logs_content_hash;

ALTER TABLE audit_logs
  DROP COLUMN IF EXISTS content_hash,
  DROP COLUMN IF EXISTS previous_hash,
  DROP COLUMN IF EXISTS hash_algorithm,
  DROP COLUMN IF EXISTS request_id;

DROP FUNCTION IF EXISTS zayd_block_audit_mutation();
DROP FUNCTION IF EXISTS zayd_set_audit_hash();
DROP FUNCTION IF EXISTS zayd_audit_canonical_json(
  uuid,
  uuid,
  text,
  text,
  uuid,
  text,
  text,
  text,
  text,
  jsonb,
  jsonb,
  jsonb,
  timestamptz,
  text
);

CREATE TRIGGER trg_audit_logs_updated_at
  BEFORE UPDATE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

DELETE FROM schema_migrations WHERE version = '0006_immutable_audit_logs';

COMMIT;
