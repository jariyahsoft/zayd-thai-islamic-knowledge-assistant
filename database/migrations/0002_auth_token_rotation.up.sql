-- TASK-03-01 — Authentication token rotation support

BEGIN;

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES auth_sessions(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  token_hash text NOT NULL,
  parent_token_hash text,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  revoked_at timestamptz,
  reuse_detected_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_refresh_tokens_token_hash UNIQUE (token_hash)
);
CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_session_active
  ON auth_refresh_tokens (session_id, expires_at) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_auth_refresh_tokens_user
  ON auth_refresh_tokens (user_id, created_at);
CREATE TRIGGER trg_auth_refresh_tokens_updated_at
  BEFORE UPDATE ON auth_refresh_tokens
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE IF NOT EXISTS auth_password_reset_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  token_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_password_reset_tokens_token_hash UNIQUE (token_hash)
);
CREATE INDEX IF NOT EXISTS idx_auth_password_reset_tokens_user_active
  ON auth_password_reset_tokens (user_id, expires_at) WHERE used_at IS NULL;

CREATE TABLE IF NOT EXISTS auth_rate_limits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket text NOT NULL,
  action text NOT NULL,
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  window_start timestamptz NOT NULL,
  blocked_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_rate_limits_bucket UNIQUE (bucket)
);
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_action_blocked
  ON auth_rate_limits (action, blocked_until);
CREATE TRIGGER trg_auth_rate_limits_updated_at
  BEFORE UPDATE ON auth_rate_limits
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

INSERT INTO schema_migrations (version, description)
VALUES ('0002_auth_token_rotation', 'Authentication refresh-token rotation, reset tokens, and rate limits')
ON CONFLICT (version) DO NOTHING;

COMMIT;
