-- TASK-03-05 — Immutable audit log hardening
-- Adds request IDs, reasons, hash chaining, and database-level append-only protections.

BEGIN;

CREATE OR REPLACE FUNCTION zayd_audit_canonical_json(
  p_id uuid,
  p_actor_user_id uuid,
  p_action text,
  p_resource_type text,
  p_resource_id uuid,
  p_outcome text,
  p_reason text,
  p_request_id text,
  p_trace_id text,
  p_before_summary jsonb,
  p_after_summary jsonb,
  p_source_context jsonb,
  p_created_at timestamptz,
  p_previous_hash text
)
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT jsonb_build_object(
    'id', p_id,
    'actor_user_id', p_actor_user_id,
    'action', p_action,
    'resource_type', p_resource_type,
    'resource_id', p_resource_id,
    'outcome', p_outcome,
    'reason', p_reason,
    'request_id', p_request_id,
    'trace_id', p_trace_id,
    'before_summary', p_before_summary,
    'after_summary', p_after_summary,
    'source_context', COALESCE(p_source_context, '{}'::jsonb),
    'created_at', p_created_at,
    'previous_hash', p_previous_hash
  )::text;
$$;

ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS reason text,
  ADD COLUMN IF NOT EXISTS request_id text,
  ADD COLUMN IF NOT EXISTS hash_algorithm text NOT NULL DEFAULT 'sha256',
  ADD COLUMN IF NOT EXISTS previous_hash text,
  ADD COLUMN IF NOT EXISTS content_hash text;

UPDATE audit_logs
SET request_id = COALESCE(request_id, trace_id)
WHERE request_id IS NULL AND trace_id IS NOT NULL;

WITH RECURSIVE ordered AS (
  SELECT
    row_number() OVER (ORDER BY created_at, id) AS rn,
    id,
    actor_user_id,
    action,
    resource_type,
    resource_id,
    outcome,
    reason,
    request_id,
    trace_id,
    before_summary,
    after_summary,
    source_context,
    created_at
  FROM audit_logs
), chain AS (
  SELECT
    rn,
    id,
    NULL::text AS computed_previous_hash,
    encode(
      digest(
        zayd_audit_canonical_json(
          id,
          actor_user_id,
          action,
          resource_type,
          resource_id,
          outcome,
          reason,
          request_id,
          trace_id,
          before_summary,
          after_summary,
          source_context,
          created_at,
          NULL::text
        ),
        'sha256'
      ),
      'hex'
    ) AS computed_content_hash
  FROM ordered
  WHERE rn = 1
  UNION ALL
  SELECT
    ordered.rn,
    ordered.id,
    chain.computed_content_hash AS computed_previous_hash,
    encode(
      digest(
        zayd_audit_canonical_json(
          ordered.id,
          ordered.actor_user_id,
          ordered.action,
          ordered.resource_type,
          ordered.resource_id,
          ordered.outcome,
          ordered.reason,
          ordered.request_id,
          ordered.trace_id,
          ordered.before_summary,
          ordered.after_summary,
          ordered.source_context,
          ordered.created_at,
          chain.computed_content_hash
        ),
        'sha256'
      ),
      'hex'
    ) AS computed_content_hash
  FROM ordered
  JOIN chain ON ordered.rn = chain.rn + 1
)
UPDATE audit_logs target
SET
  previous_hash = chain.computed_previous_hash,
  content_hash = chain.computed_content_hash
FROM chain
WHERE target.id = chain.id AND target.content_hash IS NULL;

ALTER TABLE audit_logs
  ALTER COLUMN content_hash SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_logs_content_hash ON audit_logs (content_hash);
CREATE INDEX IF NOT EXISTS idx_audit_logs_request ON audit_logs (request_id) WHERE request_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_logs_hash_chain ON audit_logs (created_at, id, previous_hash, content_hash);

CREATE OR REPLACE FUNCTION zayd_set_audit_hash()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_previous_hash text;
BEGIN
  NEW.updated_at := NEW.created_at;
  NEW.hash_algorithm := COALESCE(NEW.hash_algorithm, 'sha256');
  NEW.source_context := COALESCE(NEW.source_context, '{}'::jsonb);
  SELECT content_hash INTO v_previous_hash
  FROM audit_logs
  ORDER BY created_at DESC, id DESC
  LIMIT 1;
  NEW.previous_hash := COALESCE(NEW.previous_hash, v_previous_hash);
  NEW.content_hash := encode(
    digest(
      zayd_audit_canonical_json(
        NEW.id,
        NEW.actor_user_id,
        NEW.action,
        NEW.resource_type,
        NEW.resource_id,
        NEW.outcome,
        NEW.reason,
        NEW.request_id,
        NEW.trace_id,
        NEW.before_summary,
        NEW.after_summary,
        NEW.source_context,
        NEW.created_at,
        NEW.previous_hash
      ),
      'sha256'
    ),
    'hex'
  );
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION zayd_block_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs are append-only and cannot be updated or deleted';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_logs_updated_at ON audit_logs;
DROP TRIGGER IF EXISTS trg_audit_logs_set_hash ON audit_logs;
DROP TRIGGER IF EXISTS trg_audit_logs_no_update ON audit_logs;
DROP TRIGGER IF EXISTS trg_audit_logs_no_delete ON audit_logs;

CREATE TRIGGER trg_audit_logs_set_hash
  BEFORE INSERT ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION zayd_set_audit_hash();
CREATE TRIGGER trg_audit_logs_no_update
  BEFORE UPDATE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION zayd_block_audit_mutation();
CREATE TRIGGER trg_audit_logs_no_delete
  BEFORE DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION zayd_block_audit_mutation();

INSERT INTO schema_migrations (version, description)
VALUES ('0006_immutable_audit_logs', 'Append-only hash-chained audit logs with request IDs')
ON CONFLICT (version) DO NOTHING;

COMMIT;
