-- TASK-03-03 — Roll back RBAC permission and system-role seed data
-- Development/test rollback only.

BEGIN;

DELETE FROM auth_role_permissions
WHERE role_id IN (
  SELECT id FROM auth_roles
  WHERE name IN (
    'guest',
    'user',
    'data_operator',
    'translator',
    'reviewer',
    'senior_scholar',
    'admin',
    'auditor',
    'maintainer'
  )
);

DELETE FROM auth_user_roles
WHERE role_id IN (
  SELECT id FROM auth_roles
  WHERE name IN (
    'guest',
    'user',
    'data_operator',
    'translator',
    'reviewer',
    'senior_scholar',
    'admin',
    'auditor',
    'maintainer'
  )
);

DELETE FROM auth_roles
WHERE name IN (
  'guest',
  'user',
  'data_operator',
  'translator',
  'reviewer',
  'senior_scholar',
  'admin',
  'auditor',
  'maintainer'
)
AND is_system = true;

DELETE FROM auth_permissions
WHERE (resource, action) IN (
  ('sessions', 'revoke_own'),
  ('users', 'read_self'),
  ('users', 'read'),
  ('users', 'manage'),
  ('users', 'roles.manage'),
  ('documents', 'read'),
  ('documents', 'upload'),
  ('documents', 'edit'),
  ('documents', 'review'),
  ('documents', 'approve'),
  ('documents', 'publish'),
  ('documents', 'archive'),
  ('answers', 'review'),
  ('answers', 'invalidate'),
  ('providers', 'read'),
  ('providers', 'manage'),
  ('licenses', 'read'),
  ('licenses', 'manage'),
  ('prompts', 'manage'),
  ('models', 'manage'),
  ('audit', 'read'),
  ('audit', 'export'),
  ('feedback', 'create'),
  ('feedback', 'read'),
  ('feedback', 'manage'),
  ('conversations', 'manage_own')
);

DELETE FROM schema_migrations WHERE version = '0004_rbac_seed';

COMMIT;
