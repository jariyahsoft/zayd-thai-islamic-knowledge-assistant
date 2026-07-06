-- TASK-03-03 — RBAC permission and system-role seed data
-- Adds action-based permissions, canonical roles, and least-privilege role grants.

BEGIN;

INSERT INTO auth_permissions (resource, action, description)
VALUES
  ('sessions', 'revoke_own', 'Revoke own active sessions.'),
  ('users', 'read_self', 'Read own user profile.'),
  ('users', 'read', 'Read user records.'),
  ('users', 'manage', 'Manage user accounts.'),
  ('users', 'roles.manage', 'Grant and revoke user roles.'),
  ('documents', 'read', 'Read document metadata and review surfaces.'),
  ('documents', 'upload', 'Upload new document material.'),
  ('documents', 'edit', 'Edit document metadata and extracted text before publication.'),
  ('documents', 'review', 'Review document material and evidence.'),
  ('documents', 'approve', 'Approve restricted document work.'),
  ('documents', 'publish', 'Publish approved document versions.'),
  ('documents', 'archive', 'Archive or suspend published document material.'),
  ('answers', 'review', 'Review generated answers and retrieval evidence.'),
  ('answers', 'invalidate', 'Invalidate unsafe or unsupported answers.'),
  ('providers', 'read', 'Read provider configuration metadata.'),
  ('providers', 'manage', 'Manage provider configuration.'),
  ('licenses', 'read', 'Read source and license metadata.'),
  ('licenses', 'manage', 'Manage source license policy records.'),
  ('prompts', 'manage', 'Manage prompt versions.'),
  ('models', 'manage', 'Manage model configuration.'),
  ('audit', 'read', 'Read audit logs.'),
  ('audit', 'export', 'Export audit logs.'),
  ('feedback', 'create', 'Create feedback reports.'),
  ('feedback', 'read', 'Read feedback records.'),
  ('feedback', 'manage', 'Manage feedback queues and status.'),
  ('conversations', 'manage_own', 'Manage own conversations.')
ON CONFLICT (resource, action) DO UPDATE
SET description = EXCLUDED.description;

INSERT INTO auth_roles (name, description, is_system)
VALUES
  ('guest', 'Anonymous session with no privileged back-office access.', true),
  ('user', 'Registered user with own-session, conversation and feedback access.', true),
  ('data_operator', 'Imports and prepares documents before review.', true),
  ('translator', 'Edits translation-oriented document metadata and text.', true),
  ('reviewer', 'Reviews documents, answers and supporting evidence.', true),
  ('senior_scholar', 'Approves high-impact religious content and publishing decisions.', true),
  ('admin', 'Manages users, roles, providers, licenses, prompts and models.', true),
  ('auditor', 'Reads audit and approved operational records without mutation rights.', true),
  ('maintainer', 'Maintains provider/model/prompt configuration for releases.', true)
ON CONFLICT (name) WHERE deleted_at IS NULL DO UPDATE
SET description = EXCLUDED.description,
    is_system = true;

WITH role_permissions(role_name, resource, action) AS (
  VALUES
    ('user', 'sessions', 'revoke_own'),
    ('user', 'users', 'read_self'),
    ('user', 'feedback', 'create'),
    ('user', 'conversations', 'manage_own'),
    ('data_operator', 'sessions', 'revoke_own'),
    ('data_operator', 'users', 'read_self'),
    ('data_operator', 'documents', 'read'),
    ('data_operator', 'documents', 'upload'),
    ('data_operator', 'documents', 'edit'),
    ('data_operator', 'licenses', 'read'),
    ('translator', 'sessions', 'revoke_own'),
    ('translator', 'users', 'read_self'),
    ('translator', 'documents', 'read'),
    ('translator', 'documents', 'edit'),
    ('translator', 'documents', 'review'),
    ('translator', 'licenses', 'read'),
    ('reviewer', 'sessions', 'revoke_own'),
    ('reviewer', 'users', 'read_self'),
    ('reviewer', 'documents', 'read'),
    ('reviewer', 'documents', 'review'),
    ('reviewer', 'answers', 'review'),
    ('reviewer', 'feedback', 'read'),
    ('reviewer', 'licenses', 'read'),
    ('senior_scholar', 'sessions', 'revoke_own'),
    ('senior_scholar', 'users', 'read_self'),
    ('senior_scholar', 'documents', 'read'),
    ('senior_scholar', 'documents', 'review'),
    ('senior_scholar', 'documents', 'approve'),
    ('senior_scholar', 'documents', 'publish'),
    ('senior_scholar', 'answers', 'review'),
    ('senior_scholar', 'answers', 'invalidate'),
    ('senior_scholar', 'licenses', 'read'),
    ('admin', 'sessions', 'revoke_own'),
    ('admin', 'users', 'read_self'),
    ('admin', 'users', 'read'),
    ('admin', 'users', 'manage'),
    ('admin', 'users', 'roles.manage'),
    ('admin', 'documents', 'read'),
    ('admin', 'documents', 'upload'),
    ('admin', 'documents', 'edit'),
    ('admin', 'documents', 'review'),
    ('admin', 'documents', 'approve'),
    ('admin', 'documents', 'publish'),
    ('admin', 'documents', 'archive'),
    ('admin', 'answers', 'review'),
    ('admin', 'answers', 'invalidate'),
    ('admin', 'providers', 'read'),
    ('admin', 'providers', 'manage'),
    ('admin', 'licenses', 'read'),
    ('admin', 'licenses', 'manage'),
    ('admin', 'prompts', 'manage'),
    ('admin', 'models', 'manage'),
    ('admin', 'audit', 'read'),
    ('admin', 'feedback', 'read'),
    ('admin', 'feedback', 'manage'),
    ('auditor', 'sessions', 'revoke_own'),
    ('auditor', 'users', 'read_self'),
    ('auditor', 'users', 'read'),
    ('auditor', 'documents', 'read'),
    ('auditor', 'providers', 'read'),
    ('auditor', 'licenses', 'read'),
    ('auditor', 'audit', 'read'),
    ('auditor', 'audit', 'export'),
    ('auditor', 'feedback', 'read'),
    ('maintainer', 'sessions', 'revoke_own'),
    ('maintainer', 'users', 'read_self'),
    ('maintainer', 'providers', 'read'),
    ('maintainer', 'providers', 'manage'),
    ('maintainer', 'prompts', 'manage'),
    ('maintainer', 'models', 'manage'),
    ('maintainer', 'audit', 'read')
)
INSERT INTO auth_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM role_permissions rp
JOIN auth_roles r ON r.name = rp.role_name AND r.deleted_at IS NULL
JOIN auth_permissions p ON p.resource = rp.resource AND p.action = rp.action
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO schema_migrations (version, description)
VALUES ('0004_rbac_seed', 'RBAC system permissions, roles, and permission matrix')
ON CONFLICT (version) DO NOTHING;

COMMIT;
