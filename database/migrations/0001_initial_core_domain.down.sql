-- TASK-02-02 — Downgrade initial core-domain schema migration
-- Development/test rollback only. Production rollback requires backup/restore policy and approval.

BEGIN;

DROP TABLE IF EXISTS evaluation_results CASCADE;
DROP TABLE IF EXISTS evaluation_runs CASCADE;
DROP TABLE IF EXISTS evaluation_cases CASCADE;
DROP TABLE IF EXISTS evaluation_datasets CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS incidents CASCADE;
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS embedding_records CASCADE;
DROP TABLE IF EXISTS answers CASCADE;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS retrieval_results CASCADE;
DROP TABLE IF EXISTS retrieval_runs CASCADE;
DROP TABLE IF EXISTS citations CASCADE;
DROP TABLE IF EXISTS review_comments CASCADE;
DROP TABLE IF EXISTS approvals CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS review_tasks CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS document_pages CASCADE;
ALTER TABLE IF EXISTS documents DROP CONSTRAINT IF EXISTS fk_documents_published_version;
DROP TABLE IF EXISTS document_versions CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS policy_versions CASCADE;
DROP TABLE IF EXISTS prompt_versions CASCADE;
DROP TABLE IF EXISTS model_configurations CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
DROP TABLE IF EXISTS source_licenses CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS auth_sessions CASCADE;
DROP TABLE IF EXISTS auth_role_permissions CASCADE;
DROP TABLE IF EXISTS auth_user_roles CASCADE;
DROP TABLE IF EXISTS auth_permissions CASCADE;
DROP TABLE IF EXISTS auth_roles CASCADE;
DROP TABLE IF EXISTS auth_users CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;

DROP FUNCTION IF EXISTS zayd_validate_embedding_record() CASCADE;
DROP FUNCTION IF EXISTS zayd_validate_retrieval_result_chunk_version() CASCADE;
DROP FUNCTION IF EXISTS zayd_validate_citation_chunk_version() CASCADE;
DROP FUNCTION IF EXISTS zayd_assert_same_document_version(uuid, uuid) CASCADE;
DROP FUNCTION IF EXISTS zayd_set_updated_at() CASCADE;

DROP TYPE IF EXISTS evaluation_status CASCADE;
DROP TYPE IF EXISTS provider_status CASCADE;
DROP TYPE IF EXISTS provider_type CASCADE;
DROP TYPE IF EXISTS incident_status CASCADE;
DROP TYPE IF EXISTS incident_severity CASCADE;
DROP TYPE IF EXISTS feedback_status CASCADE;
DROP TYPE IF EXISTS risk_level CASCADE;
DROP TYPE IF EXISTS citation_type CASCADE;
DROP TYPE IF EXISTS approval_level CASCADE;
DROP TYPE IF EXISTS review_decision CASCADE;
DROP TYPE IF EXISTS document_status CASCADE;
DROP TYPE IF EXISTS permission_state CASCADE;
DROP TYPE IF EXISTS license_status CASCADE;
DROP TYPE IF EXISTS madhhab CASCADE;
DROP TYPE IF EXISTS language_code CASCADE;
DROP TYPE IF EXISTS source_type CASCADE;

-- Extensions are intentionally left installed. They are database capabilities and may be shared by other migrations.

COMMIT;
