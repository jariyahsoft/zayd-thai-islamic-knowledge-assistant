-- TASK-03-04 — MFA support for privileged users
-- Adds TOTP secrets, single-use recovery codes, and short-lived challenges.

BEGIN;

CREATE TABLE IF NOT EXISTS auth_mfa_secrets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  secret text NOT NULL,
  confirmed_at timestamptz,
  recovery_codes_rotated_at timestamptz,
  last_used_counter integer NOT NULL DEFAULT 0 CHECK (last_used_counter >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_mfa_secrets_user UNIQUE (user_id)
);
CREATE INDEX IF NOT EXISTS idx_auth_mfa_secrets_user
  ON auth_mfa_secrets (user_id);
CREATE TRIGGER trg_auth_mfa_secrets_updated_at
  BEFORE UPDATE ON auth_mfa_secrets
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE IF NOT EXISTS auth_mfa_recovery_codes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  code_hash text NOT NULL,
  issued_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_mfa_recovery_codes_hash UNIQUE (code_hash)
);
CREATE INDEX IF NOT EXISTS idx_auth_mfa_recovery_codes_user_active
  ON auth_mfa_recovery_codes (user_id, expires_at) WHERE used_at IS NULL;
CREATE TRIGGER trg_auth_mfa_recovery_codes_updated_at
  BEFORE UPDATE ON auth_mfa_recovery_codes
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE IF NOT EXISTS auth_mfa_challenges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  challenge_code text NOT NULL,
  issued_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_mfa_challenges_code UNIQUE (challenge_code)
);
CREATE INDEX IF NOT EXISTS idx_auth_mfa_challenges_user_active
  ON auth_mfa_challenges (user_id, expires_at) WHERE consumed_at IS NULL;
CREATE TRIGGER trg_auth_mfa_challenges_updated_at
  BEFORE UPDATE ON auth_mfa_challenges
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

INSERT INTO schema_migrations (version, description)
VALUES ('0005_mfa_privileged', 'TOTP secrets, recovery codes, and challenges for privileged MFA')
ON CONFLICT (version) DO NOTHING;

COMMIT;
