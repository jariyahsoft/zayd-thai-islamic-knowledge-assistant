-- TASK-02-02 — Initial core-domain schema migration
-- PostgreSQL 16 + pgvector. Domain behavior remains in services; this file defines schema integrity.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE schema_migrations (
  version text PRIMARY KEY,
  description text NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TYPE source_type AS ENUM (
  'book', 'fatwa_site', 'quran', 'hadith_collection', 'article', 'lecture', 'external_provider', 'other'
);
CREATE TYPE language_code AS ENUM ('th', 'ar', 'en', 'mixed');
CREATE TYPE madhhab AS ENUM ('hanafi', 'maliki', 'shafii', 'hanbali', 'multi', 'not_applicable', 'unknown');
CREATE TYPE license_status AS ENUM (
  'unknown', 'review_required', 'ephemeral_cache_only', 'persistent_private',
  'persistent_redistributable', 'prohibited', 'expired'
);
CREATE TYPE permission_state AS ENUM ('unknown', 'allowed', 'prohibited', 'conditional');
CREATE TYPE document_status AS ENUM (
  'draft', 'uploaded', 'parsing', 'ai_extracted', 'in_review', 'changes_requested',
  'rejected', 'scholar_review', 'scholar_approved', 'published', 'suspended',
  'archived', 'new_version'
);
CREATE TYPE review_decision AS ENUM (
  'approve', 'request_changes', 'reject', 'escalate', 'mark_duplicate', 'mark_license_issue'
);
CREATE TYPE approval_level AS ENUM ('level_0_system', 'level_1_reviewer', 'level_2_scholar', 'level_3_board');
CREATE TYPE citation_type AS ENUM ('quran', 'hadith', 'book', 'fatwa', 'article', 'web', 'other');
CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'restricted');
CREATE TYPE feedback_status AS ENUM ('open', 'triaged', 'linked_to_incident', 'resolved', 'dismissed');
CREATE TYPE incident_severity AS ENUM ('p0', 'p1', 'p2', 'p3');
CREATE TYPE incident_status AS ENUM ('open', 'triaged', 'mitigated', 'resolved', 'closed');
CREATE TYPE provider_type AS ENUM ('llm', 'embedding', 'reranker', 'knowledge', 'storage', 'auth');
CREATE TYPE provider_status AS ENUM ('enabled', 'disabled', 'degraded');
CREATE TYPE evaluation_status AS ENUM ('draft', 'ready', 'running', 'passed', 'failed', 'archived');

CREATE FUNCTION zayd_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE auth_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email citext NOT NULL,
  display_name text NOT NULL,
  password_hash text,
  mfa_enabled boolean NOT NULL DEFAULT false,
  preferred_language language_code NOT NULL DEFAULT 'th',
  preferred_madhhab madhhab NOT NULL DEFAULT 'shafii',
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled', 'locked', 'pending')),
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE UNIQUE INDEX uq_auth_users_email_active ON auth_users (lower(email::text)) WHERE deleted_at IS NULL;
CREATE INDEX idx_auth_users_status ON auth_users (status);
CREATE TRIGGER trg_auth_users_updated_at BEFORE UPDATE ON auth_users FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE auth_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  is_system boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE UNIQUE INDEX uq_auth_roles_name_active ON auth_roles (name) WHERE deleted_at IS NULL;
CREATE INDEX idx_auth_roles_system ON auth_roles (is_system);
CREATE TRIGGER trg_auth_roles_updated_at BEFORE UPDATE ON auth_roles FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE auth_permissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resource text NOT NULL,
  action text NOT NULL,
  description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_permissions_resource_action UNIQUE (resource, action)
);
CREATE INDEX idx_auth_permissions_resource ON auth_permissions (resource);
CREATE TRIGGER trg_auth_permissions_updated_at BEFORE UPDATE ON auth_permissions FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE auth_user_roles (
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  role_id uuid NOT NULL REFERENCES auth_roles(id) ON DELETE RESTRICT,
  granted_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_user_roles_user_role UNIQUE (user_id, role_id)
);
CREATE INDEX idx_auth_user_roles_role ON auth_user_roles (role_id);
CREATE INDEX idx_auth_user_roles_granted_by ON auth_user_roles (granted_by);
CREATE TRIGGER trg_auth_user_roles_updated_at BEFORE UPDATE ON auth_user_roles FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE auth_role_permissions (
  role_id uuid NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES auth_permissions(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_role_permissions_role_permission UNIQUE (role_id, permission_id)
);
CREATE INDEX idx_auth_role_permissions_permission ON auth_role_permissions (permission_id);
CREATE TRIGGER trg_auth_role_permissions_updated_at BEFORE UPDATE ON auth_role_permissions FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE auth_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  session_hash text NOT NULL,
  ip_hash text,
  user_agent_hash text,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_auth_sessions_session_hash UNIQUE (session_hash)
);
CREATE INDEX idx_auth_sessions_user_active ON auth_sessions (user_id, expires_at) WHERE revoked_at IS NULL;
CREATE TRIGGER trg_auth_sessions_updated_at BEFORE UPDATE ON auth_sessions FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  source_type source_type NOT NULL,
  owner text,
  website text,
  language language_code NOT NULL,
  country char(2),
  reliability_level integer NOT NULL CHECK (reliability_level BETWEEN 1 AND 5),
  is_active boolean NOT NULL DEFAULT true,
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  updated_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE UNIQUE INDEX uq_sources_name_owner_active ON sources (name, owner) WHERE deleted_at IS NULL;
CREATE INDEX idx_sources_language_type_active ON sources (language, source_type, is_active);
CREATE INDEX idx_sources_reliability ON sources (reliability_level);
CREATE INDEX idx_sources_created_by ON sources (created_by);
CREATE INDEX idx_sources_updated_by ON sources (updated_by);
CREATE TRIGGER trg_sources_updated_at BEFORE UPDATE ON sources FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE source_licenses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  license_name text NOT NULL,
  license_version text,
  status license_status NOT NULL DEFAULT 'unknown',
  storage_permission permission_state NOT NULL DEFAULT 'unknown',
  embedding_permission permission_state NOT NULL DEFAULT 'unknown',
  commercial_use permission_state NOT NULL DEFAULT 'unknown',
  redistribution permission_state NOT NULL DEFAULT 'unknown',
  attribution_required boolean NOT NULL DEFAULT true,
  attribution_template text,
  permission_document_key text,
  valid_from date,
  valid_until date,
  notes text,
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  updated_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0),
  CONSTRAINT uq_source_licenses_source_name_valid_from UNIQUE (source_id, license_name, valid_from),
  CONSTRAINT ck_source_licenses_valid_range CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from),
  CONSTRAINT ck_source_licenses_fail_closed CHECK (
    status NOT IN ('persistent_private', 'persistent_redistributable')
    OR storage_permission IN ('allowed', 'conditional')
  )
);
CREATE INDEX idx_source_licenses_source ON source_licenses (source_id);
CREATE INDEX idx_source_licenses_status ON source_licenses (status);
CREATE INDEX idx_source_licenses_expiry ON source_licenses (valid_until) WHERE valid_until IS NOT NULL;
CREATE INDEX idx_source_licenses_created_by ON source_licenses (created_by);
CREATE INDEX idx_source_licenses_updated_by ON source_licenses (updated_by);
CREATE TRIGGER trg_source_licenses_updated_at BEFORE UPDATE ON source_licenses FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE providers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  provider_type provider_type NOT NULL,
  status provider_status NOT NULL DEFAULT 'disabled',
  base_url text,
  secret_ref text,
  terms_url text,
  data_policy_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  updated_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE UNIQUE INDEX uq_providers_name_type_active ON providers (name, provider_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_providers_type_status ON providers (provider_type, status);
CREATE INDEX idx_providers_created_by ON providers (created_by);
CREATE INDEX idx_providers_updated_by ON providers (updated_by);
CREATE TRIGGER trg_providers_updated_at BEFORE UPDATE ON providers FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE model_configurations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE RESTRICT,
  model_name text NOT NULL,
  model_type text NOT NULL CHECK (model_type IN ('llm', 'embedding', 'reranker', 'classification')),
  configuration_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_default boolean NOT NULL DEFAULT false,
  status provider_status NOT NULL DEFAULT 'disabled',
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0)
);
CREATE UNIQUE INDEX uq_model_configurations_provider_model_active ON model_configurations (provider_id, model_name) WHERE deleted_at IS NULL;
CREATE INDEX idx_model_configurations_type_status ON model_configurations (model_type, status);
CREATE INDEX idx_model_configurations_created_by ON model_configurations (created_by);
CREATE TRIGGER trg_model_configurations_updated_at BEFORE UPDATE ON model_configurations FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE prompt_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  version text NOT NULL,
  prompt_hash text NOT NULL,
  prompt_body text NOT NULL,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'deprecated', 'archived')),
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  approved_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_prompt_versions_name_version UNIQUE (name, version)
);
CREATE INDEX idx_prompt_versions_status ON prompt_versions (status);
CREATE INDEX idx_prompt_versions_created_by ON prompt_versions (created_by);
CREATE INDEX idx_prompt_versions_approved_by ON prompt_versions (approved_by);
CREATE TRIGGER trg_prompt_versions_updated_at BEFORE UPDATE ON prompt_versions FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE policy_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_name text NOT NULL,
  version text NOT NULL,
  policy_hash text NOT NULL,
  policy_json jsonb NOT NULL,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'deprecated', 'archived')),
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  approved_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_policy_versions_name_version UNIQUE (policy_name, version)
);
CREATE INDEX idx_policy_versions_status ON policy_versions (status);
CREATE INDEX idx_policy_versions_created_by ON policy_versions (created_by);
CREATE INDEX idx_policy_versions_approved_by ON policy_versions (approved_by);
CREATE TRIGGER trg_policy_versions_updated_at BEFORE UPDATE ON policy_versions FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
  source_license_id uuid NOT NULL REFERENCES source_licenses(id) ON DELETE RESTRICT,
  canonical_id text NOT NULL,
  document_type text NOT NULL,
  title text NOT NULL,
  author text,
  translator text,
  publisher text,
  edition text,
  language language_code NOT NULL,
  madhhab madhhab NOT NULL DEFAULT 'unknown',
  review_status document_status NOT NULL DEFAULT 'draft',
  published_version_id uuid,
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  updated_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  row_version integer NOT NULL DEFAULT 1 CHECK (row_version > 0),
  CONSTRAINT ck_documents_published_has_version CHECK (review_status <> 'published' OR published_version_id IS NOT NULL)
);
CREATE UNIQUE INDEX uq_documents_source_canonical_active ON documents (source_id, canonical_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_review_status ON documents (review_status);
CREATE INDEX idx_documents_source_license ON documents (source_id, source_license_id);
CREATE INDEX idx_documents_language_madhhab ON documents (language, madhhab);
CREATE INDEX idx_documents_title_fts ON documents USING gin (to_tsvector('simple', title));
CREATE INDEX idx_documents_published_version ON documents (published_version_id);
CREATE INDEX idx_documents_created_by ON documents (created_by);
CREATE INDEX idx_documents_updated_by ON documents (updated_by);
CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE document_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
  version_number integer NOT NULL CHECK (version_number > 0),
  status document_status NOT NULL DEFAULT 'uploaded',
  content_hash text NOT NULL,
  original_file_key text,
  extracted_text text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  frozen_at timestamptz,
  CONSTRAINT uq_document_versions_document_version UNIQUE (document_id, version_number),
  CONSTRAINT uq_document_versions_document_hash UNIQUE (document_id, content_hash),
  CONSTRAINT ck_document_versions_published_frozen CHECK (status <> 'published' OR frozen_at IS NOT NULL)
);
CREATE INDEX idx_document_versions_document_status ON document_versions (document_id, status);
CREATE INDEX idx_document_versions_content_hash ON document_versions (content_hash);
CREATE INDEX idx_document_versions_created_by ON document_versions (created_by);
CREATE TRIGGER trg_document_versions_updated_at BEFORE UPDATE ON document_versions FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

ALTER TABLE documents
  ADD CONSTRAINT fk_documents_published_version
  FOREIGN KEY (published_version_id) REFERENCES document_versions(id)
  ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE document_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  page_number integer NOT NULL CHECK (page_number > 0),
  source_locator text,
  text_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_document_pages_version_page UNIQUE (document_version_id, page_number)
);
CREATE INDEX idx_document_pages_version ON document_pages (document_version_id);
CREATE TRIGGER trg_document_pages_updated_at BEFORE UPDATE ON document_pages FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL CHECK (chunk_index >= 0),
  content text NOT NULL,
  content_normalized text NOT NULL,
  content_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('simple', content_normalized)) STORED,
  token_count integer NOT NULL CHECK (token_count > 0),
  page_start integer,
  page_end integer,
  section text,
  reference text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_published boolean NOT NULL DEFAULT false,
  chunking_strategy_version text NOT NULL,
  content_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_document_chunks_version_index UNIQUE (document_version_id, chunk_index),
  CONSTRAINT uq_document_chunks_version_hash UNIQUE (document_version_id, content_hash),
  CONSTRAINT ck_document_chunks_page_range CHECK (page_start IS NULL OR page_end IS NULL OR page_end >= page_start)
);
CREATE INDEX idx_document_chunks_published_version ON document_chunks (document_version_id, is_published);
CREATE INDEX idx_document_chunks_reference ON document_chunks (reference) WHERE reference IS NOT NULL;
CREATE INDEX idx_document_chunks_fts ON document_chunks USING gin (content_tsvector) WHERE is_published = true;
CREATE TRIGGER trg_document_chunks_updated_at BEFORE UPDATE ON document_chunks FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE review_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  assigned_to uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  review_level approval_level NOT NULL,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'completed', 'cancelled')),
  due_at timestamptz,
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_review_tasks_open_level ON review_tasks (document_version_id, review_level) WHERE status IN ('open', 'in_progress');
CREATE INDEX idx_review_tasks_queue ON review_tasks (status, review_level, due_at);
CREATE INDEX idx_review_tasks_assigned_to ON review_tasks (assigned_to);
CREATE INDEX idx_review_tasks_created_by ON review_tasks (created_by);
CREATE TRIGGER trg_review_tasks_updated_at BEFORE UPDATE ON review_tasks FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  review_task_id uuid NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
  reviewer_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  decision review_decision NOT NULL,
  comments text NOT NULL,
  fields_changed jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_reviews_task_created ON reviews (review_task_id, created_at);
CREATE INDEX idx_reviews_reviewer ON reviews (reviewer_id);
CREATE TRIGGER trg_reviews_updated_at BEFORE UPDATE ON reviews FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  review_id uuid NOT NULL REFERENCES reviews(id) ON DELETE RESTRICT,
  approval_level approval_level NOT NULL,
  approver_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  valid_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_approvals_version_level UNIQUE (document_version_id, approval_level)
);
CREATE INDEX idx_approvals_valid_until ON approvals (valid_until) WHERE valid_until IS NOT NULL;
CREATE INDEX idx_approvals_review ON approvals (review_id);
CREATE INDEX idx_approvals_approver ON approvals (approver_id);
CREATE TRIGGER trg_approvals_updated_at BEFORE UPDATE ON approvals FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE review_comments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  review_task_id uuid NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
  author_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  body text NOT NULL,
  anchor_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);
CREATE INDEX idx_review_comments_task_created ON review_comments (review_task_id, created_at);
CREATE INDEX idx_review_comments_author ON review_comments (author_id);
CREATE TRIGGER trg_review_comments_updated_at BEFORE UPDATE ON review_comments FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE citations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_reference text NOT NULL,
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE RESTRICT,
  chunk_id uuid NOT NULL REFERENCES document_chunks(id) ON DELETE RESTRICT,
  citation_type citation_type NOT NULL,
  display_title text NOT NULL,
  arabic_text text,
  thai_translation text,
  hadith_grade text,
  volume text,
  page text,
  verified boolean NOT NULL DEFAULT false,
  invalidated_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_citations_canonical_version UNIQUE (canonical_reference, document_version_id)
);
CREATE INDEX idx_citations_chunk ON citations (chunk_id);
CREATE INDEX idx_citations_active ON citations (verified, invalidated_at);
CREATE INDEX idx_citations_reference ON citations (canonical_reference);
CREATE INDEX idx_citations_version ON citations (document_version_id);
CREATE TRIGGER trg_citations_updated_at BEFORE UPDATE ON citations FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE retrieval_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id text NOT NULL,
  trace_id text,
  query_original text NOT NULL,
  query_normalized text NOT NULL,
  query_expansions jsonb NOT NULL DEFAULT '[]'::jsonb,
  filters jsonb NOT NULL DEFAULT '{}'::jsonb,
  retriever_version text NOT NULL,
  evidence_sufficient boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_retrieval_runs_request UNIQUE (request_id)
);
CREATE INDEX idx_retrieval_runs_created ON retrieval_runs (created_at);
CREATE INDEX idx_retrieval_runs_trace ON retrieval_runs (trace_id) WHERE trace_id IS NOT NULL;
CREATE TRIGGER trg_retrieval_runs_updated_at BEFORE UPDATE ON retrieval_runs FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE retrieval_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  retrieval_run_id uuid NOT NULL REFERENCES retrieval_runs(id) ON DELETE CASCADE,
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE RESTRICT,
  chunk_id uuid NOT NULL REFERENCES document_chunks(id) ON DELETE RESTRICT,
  citation_id uuid REFERENCES citations(id) ON DELETE SET NULL,
  rank integer NOT NULL CHECK (rank > 0),
  score_exact numeric,
  score_full_text numeric,
  score_vector numeric,
  score_reranker numeric,
  score_final numeric NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_retrieval_results_run_rank UNIQUE (retrieval_run_id, rank)
);
CREATE INDEX idx_retrieval_results_run ON retrieval_results (retrieval_run_id, rank);
CREATE INDEX idx_retrieval_results_chunk ON retrieval_results (chunk_id);
CREATE INDEX idx_retrieval_results_version ON retrieval_results (document_version_id);
CREATE INDEX idx_retrieval_results_citation ON retrieval_results (citation_id);
CREATE TRIGGER trg_retrieval_results_updated_at BEFORE UPDATE ON retrieval_results FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  guest_session_id text,
  title text,
  language language_code NOT NULL DEFAULT 'th',
  madhhab madhhab NOT NULL DEFAULT 'shafii',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);
CREATE INDEX idx_conversations_user_updated ON conversations (user_id, updated_at) WHERE deleted_at IS NULL;
CREATE TRIGGER trg_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  sender_type text NOT NULL CHECK (sender_type IN ('user', 'assistant', 'system')),
  body text NOT NULL,
  body_hash text NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);
CREATE INDEX idx_messages_conversation_created ON messages (conversation_id, created_at);
CREATE TRIGGER trg_messages_updated_at BEFORE UPDATE ON messages FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE answers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
  retrieval_run_id uuid NOT NULL REFERENCES retrieval_runs(id) ON DELETE RESTRICT,
  model_configuration_id uuid NOT NULL REFERENCES model_configurations(id) ON DELETE RESTRICT,
  prompt_version_id uuid NOT NULL REFERENCES prompt_versions(id) ON DELETE RESTRICT,
  policy_version_id uuid NOT NULL REFERENCES policy_versions(id) ON DELETE RESTRICT,
  risk_level risk_level NOT NULL,
  madhhab madhhab NOT NULL,
  answer_json jsonb NOT NULL,
  confidence_level text NOT NULL CHECK (confidence_level IN ('low', 'medium', 'high')),
  evidence_sufficient boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  invalidated_at timestamptz,
  CONSTRAINT uq_answers_message UNIQUE (message_id)
);
CREATE INDEX idx_answers_policy_prompt_model ON answers (policy_version_id, prompt_version_id, model_configuration_id);
CREATE INDEX idx_answers_invalidated ON answers (invalidated_at) WHERE invalidated_at IS NOT NULL;
CREATE INDEX idx_answers_retrieval_run ON answers (retrieval_run_id);
CREATE INDEX idx_answers_model_configuration ON answers (model_configuration_id);
CREATE TRIGGER trg_answers_updated_at BEFORE UPDATE ON answers FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE embedding_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  chunk_id uuid NOT NULL REFERENCES document_chunks(id) ON DELETE CASCADE,
  model_configuration_id uuid NOT NULL REFERENCES model_configurations(id) ON DELETE RESTRICT,
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE RESTRICT,
  embedding vector(1536) NOT NULL,
  embedding_hash text NOT NULL,
  dimension integer NOT NULL CHECK (dimension = 1536),
  status text NOT NULL DEFAULT 'staged' CHECK (status IN ('staged', 'active', 'invalidated')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_embedding_records_chunk_model UNIQUE (chunk_id, model_configuration_id)
);
CREATE INDEX idx_embedding_records_chunk ON embedding_records (chunk_id);
CREATE INDEX idx_embedding_records_model_active ON embedding_records (model_configuration_id, status);
CREATE INDEX idx_embedding_records_provider ON embedding_records (provider_id);
CREATE INDEX idx_embedding_records_version ON embedding_records (document_version_id);
CREATE INDEX idx_embedding_records_vector ON embedding_records USING hnsw (embedding vector_cosine_ops) WHERE status = 'active';
CREATE TRIGGER trg_embedding_records_updated_at BEFORE UPDATE ON embedding_records FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  answer_id uuid REFERENCES answers(id) ON DELETE SET NULL,
  citation_id uuid REFERENCES citations(id) ON DELETE SET NULL,
  category text NOT NULL,
  body text NOT NULL,
  status feedback_status NOT NULL DEFAULT 'open',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);
CREATE INDEX idx_feedback_status_created ON feedback (status, created_at);
CREATE INDEX idx_feedback_user ON feedback (user_id);
CREATE INDEX idx_feedback_answer ON feedback (answer_id);
CREATE INDEX idx_feedback_citation ON feedback (citation_id);
CREATE TRIGGER trg_feedback_updated_at BEFORE UPDATE ON feedback FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  feedback_id uuid REFERENCES feedback(id) ON DELETE SET NULL,
  severity incident_severity NOT NULL,
  status incident_status NOT NULL DEFAULT 'open',
  summary text NOT NULL,
  affected_answer_id uuid REFERENCES answers(id) ON DELETE SET NULL,
  affected_document_id uuid REFERENCES documents(id) ON DELETE SET NULL,
  affected_citation_id uuid REFERENCES citations(id) ON DELETE SET NULL,
  opened_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  closed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_incidents_severity_status ON incidents (severity, status, created_at);
CREATE INDEX idx_incidents_feedback ON incidents (feedback_id);
CREATE INDEX idx_incidents_answer ON incidents (affected_answer_id);
CREATE INDEX idx_incidents_document ON incidents (affected_document_id);
CREATE INDEX idx_incidents_citation ON incidents (affected_citation_id);
CREATE INDEX idx_incidents_opened_by ON incidents (opened_by);
CREATE TRIGGER trg_incidents_updated_at BEFORE UPDATE ON incidents FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid,
  outcome text NOT NULL CHECK (outcome IN ('success', 'failure', 'denied', 'error')),
  request_id text,
  trace_id text,
  before_summary jsonb,
  after_summary jsonb,
  source_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_logs_resource ON audit_logs (resource_type, resource_id, created_at);
CREATE INDEX idx_audit_logs_actor ON audit_logs (actor_user_id, created_at);
CREATE INDEX idx_audit_logs_trace ON audit_logs (trace_id) WHERE trace_id IS NOT NULL;
CREATE TRIGGER trg_audit_logs_updated_at BEFORE UPDATE ON audit_logs FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE evaluation_datasets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  version text NOT NULL,
  license_status license_status NOT NULL DEFAULT 'review_required',
  manifest_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  status evaluation_status NOT NULL DEFAULT 'draft',
  created_by uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_datasets_name_version UNIQUE (name, version)
);
CREATE INDEX idx_evaluation_datasets_status ON evaluation_datasets (status);
CREATE INDEX idx_evaluation_datasets_created_by ON evaluation_datasets (created_by);
CREATE TRIGGER trg_evaluation_datasets_updated_at BEFORE UPDATE ON evaluation_datasets FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE evaluation_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id uuid NOT NULL REFERENCES evaluation_datasets(id) ON DELETE CASCADE,
  case_key text NOT NULL,
  question text NOT NULL,
  expected_citations jsonb NOT NULL DEFAULT '[]'::jsonb,
  expected_behavior jsonb NOT NULL DEFAULT '{}'::jsonb,
  risk_level risk_level NOT NULL DEFAULT 'low',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_cases_dataset_case UNIQUE (dataset_id, case_key)
);
CREATE INDEX idx_evaluation_cases_dataset ON evaluation_cases (dataset_id);
CREATE TRIGGER trg_evaluation_cases_updated_at BEFORE UPDATE ON evaluation_cases FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE evaluation_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id uuid NOT NULL REFERENCES evaluation_datasets(id) ON DELETE RESTRICT,
  model_configuration_id uuid NOT NULL REFERENCES model_configurations(id) ON DELETE RESTRICT,
  prompt_version_id uuid NOT NULL REFERENCES prompt_versions(id) ON DELETE RESTRICT,
  policy_version_id uuid NOT NULL REFERENCES policy_versions(id) ON DELETE RESTRICT,
  status evaluation_status NOT NULL DEFAULT 'running',
  metrics_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_evaluation_runs_dataset_status ON evaluation_runs (dataset_id, status, started_at);
CREATE INDEX idx_evaluation_runs_model ON evaluation_runs (model_configuration_id);
CREATE INDEX idx_evaluation_runs_prompt ON evaluation_runs (prompt_version_id);
CREATE INDEX idx_evaluation_runs_policy ON evaluation_runs (policy_version_id);
CREATE TRIGGER trg_evaluation_runs_updated_at BEFORE UPDATE ON evaluation_runs FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE TABLE evaluation_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_run_id uuid NOT NULL REFERENCES evaluation_runs(id) ON DELETE CASCADE,
  evaluation_case_id uuid NOT NULL REFERENCES evaluation_cases(id) ON DELETE RESTRICT,
  answer_id uuid REFERENCES answers(id) ON DELETE SET NULL,
  passed boolean NOT NULL,
  scores_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  failure_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_results_run_case UNIQUE (evaluation_run_id, evaluation_case_id)
);
CREATE INDEX idx_evaluation_results_run_passed ON evaluation_results (evaluation_run_id, passed);
CREATE INDEX idx_evaluation_results_case ON evaluation_results (evaluation_case_id);
CREATE INDEX idx_evaluation_results_answer ON evaluation_results (answer_id);
CREATE TRIGGER trg_evaluation_results_updated_at BEFORE UPDATE ON evaluation_results FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();

CREATE FUNCTION zayd_assert_same_document_version(child_chunk_id uuid, child_document_version_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE actual_document_version_id uuid;
BEGIN
  SELECT document_version_id INTO actual_document_version_id
  FROM document_chunks
  WHERE id = child_chunk_id;

  IF actual_document_version_id IS NULL THEN
    RAISE EXCEPTION 'Referenced chunk does not exist: %', child_chunk_id
      USING ERRCODE = '23503';
  END IF;

  IF actual_document_version_id <> child_document_version_id THEN
    RAISE EXCEPTION 'Chunk % does not belong to document version %', child_chunk_id, child_document_version_id
      USING ERRCODE = '23514';
  END IF;
END;
$$;

CREATE FUNCTION zayd_validate_citation_chunk_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM zayd_assert_same_document_version(NEW.chunk_id, NEW.document_version_id);
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_citations_chunk_version BEFORE INSERT OR UPDATE ON citations FOR EACH ROW EXECUTE FUNCTION zayd_validate_citation_chunk_version();

CREATE FUNCTION zayd_validate_retrieval_result_chunk_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  PERFORM zayd_assert_same_document_version(NEW.chunk_id, NEW.document_version_id);
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_retrieval_results_chunk_version BEFORE INSERT OR UPDATE ON retrieval_results FOR EACH ROW EXECUTE FUNCTION zayd_validate_retrieval_result_chunk_version();

CREATE FUNCTION zayd_validate_embedding_record()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE chunk_published boolean;
DECLARE version_status document_status;
DECLARE license_status_value license_status;
DECLARE embedding_permission_value permission_state;
BEGIN
  PERFORM zayd_assert_same_document_version(NEW.chunk_id, NEW.document_version_id);

  IF NEW.status = 'active' THEN
    SELECT c.is_published, dv.status, sl.status, sl.embedding_permission
      INTO chunk_published, version_status, license_status_value, embedding_permission_value
    FROM document_chunks c
    JOIN document_versions dv ON dv.id = c.document_version_id
    JOIN documents d ON d.id = dv.document_id
    JOIN source_licenses sl ON sl.id = d.source_license_id
    WHERE c.id = NEW.chunk_id;

    IF chunk_published IS DISTINCT FROM true OR version_status <> 'published' THEN
      RAISE EXCEPTION 'Active embeddings require a published chunk and document version'
        USING ERRCODE = '23514';
    END IF;

    IF license_status_value NOT IN ('persistent_private', 'persistent_redistributable')
       OR embedding_permission_value NOT IN ('allowed', 'conditional') THEN
      RAISE EXCEPTION 'Active embeddings require valid license and embedding permission'
        USING ERRCODE = '23514';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_embedding_records_integrity BEFORE INSERT OR UPDATE ON embedding_records FOR EACH ROW EXECUTE FUNCTION zayd_validate_embedding_record();

INSERT INTO schema_migrations (version, description)
VALUES ('0001_initial_core_domain', 'Initial core-domain schema for TASK-02-02');

COMMIT;
