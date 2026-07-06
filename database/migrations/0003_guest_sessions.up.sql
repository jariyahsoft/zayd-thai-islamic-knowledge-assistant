-- TASK-03-02 — Guest sessions support
-- Anonymous, TTL-bound sessions with per-session message quotas.

BEGIN;

CREATE TABLE IF NOT EXISTS guest_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_token_hash text NOT NULL,
  ip_hash text,
  user_agent_hash text,
  converted_user_id uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  message_quota integer NOT NULL DEFAULT 10 CHECK (message_quota > 0),
  messages_used integer NOT NULL DEFAULT 0 CHECK (messages_used >= 0),
  expires_at timestamptz NOT NULL,
  last_seen_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_guest_sessions_token_hash UNIQUE (session_token_hash)
);

CREATE INDEX IF NOT EXISTS idx_guest_sessions_expiry
  ON guest_sessions (expires_at) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_guest_sessions_converted_user
  ON guest_sessions (converted_user_id);
CREATE TRIGGER trg_guest_sessions_updated_at
  BEFORE UPDATE ON guest_sessions
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

INSERT INTO schema_migrations (version, description)
VALUES ('0003_guest_sessions', 'Anonymous guest sessions with TTL and message quota')
ON CONFLICT (version) DO NOTHING;

COMMIT;
