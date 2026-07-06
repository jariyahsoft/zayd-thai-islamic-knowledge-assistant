-- TASK-03-01 — Roll back authentication token rotation support
-- Development/test rollback only.

BEGIN;

DROP TABLE IF EXISTS auth_rate_limits CASCADE;
DROP TABLE IF EXISTS auth_password_reset_tokens CASCADE;
DROP TABLE IF EXISTS auth_refresh_tokens CASCADE;

DELETE FROM schema_migrations WHERE version = '0002_auth_token_rotation';

COMMIT;
