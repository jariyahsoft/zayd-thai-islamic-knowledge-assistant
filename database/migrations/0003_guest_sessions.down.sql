-- TASK-03-02 — Roll back guest sessions support
-- Development/test rollback only.

BEGIN;

DROP TABLE IF EXISTS guest_sessions CASCADE;

DELETE FROM schema_migrations WHERE version = '0003_guest_sessions';

COMMIT;
