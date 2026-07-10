ALTER TABLE evaluation_datasets
  ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'private';

ALTER TABLE evaluation_cases
  ADD COLUMN IF NOT EXISTS schema_version text NOT NULL DEFAULT 'evaluation-case-v1',
  ADD COLUMN IF NOT EXISTS case_type text NOT NULL DEFAULT 'open_ended',
  ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'private',
  ADD COLUMN IF NOT EXISTS reviewer_status text NOT NULL DEFAULT 'draft',
  ADD COLUMN IF NOT EXISTS reviewed_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS choices_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS license_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS provenance_json jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_evaluation_cases_visibility
  ON evaluation_cases (dataset_id, visibility, reviewer_status, case_type);

INSERT INTO auth_permissions (resource, action, description) VALUES
  ('evaluations', 'read', 'Read authorized evaluation datasets and cases.'),
  ('evaluations', 'manage', 'Create and manage evaluation datasets and cases.')
ON CONFLICT (resource, action) DO UPDATE SET description = EXCLUDED.description;

WITH grants(role_name, action) AS (VALUES
  ('reviewer', 'read'), ('senior_scholar', 'read'), ('senior_scholar', 'manage'),
  ('admin', 'read'), ('admin', 'manage'), ('auditor', 'read')
)
INSERT INTO auth_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM grants g
JOIN auth_roles r ON r.name = g.role_name AND r.deleted_at IS NULL
JOIN auth_permissions p ON p.resource = 'evaluations' AND p.action = g.action
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO schema_migrations (version, description)
VALUES ('0017_evaluation_case_schema', 'Versioned evaluation case schema and visibility controls')
ON CONFLICT (version) DO NOTHING;
