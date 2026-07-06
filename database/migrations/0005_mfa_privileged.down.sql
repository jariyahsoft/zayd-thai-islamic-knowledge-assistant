-- TASK-03-04 — Roll back MFA support for privileged users
-- Development/test rollback only.

BEGIN;

DROP TABLE IF EXISTS auth_mfa_challenges CASCADE;
DROP TABLE IF EXISTS auth_mfa_recovery_codes CASCADE;
DROP TABLE IF EXISTS auth_mfa_secrets CASCADE;

DELETE FROM schema_migrations WHERE version = '0005_mfa_privileged';

COMMIT;
