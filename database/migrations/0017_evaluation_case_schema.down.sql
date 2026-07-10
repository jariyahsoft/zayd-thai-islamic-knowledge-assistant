DELETE FROM auth_role_permissions WHERE permission_id IN (
  SELECT id FROM auth_permissions WHERE resource = 'evaluations'
);
DELETE FROM auth_permissions WHERE resource = 'evaluations';
DROP INDEX IF EXISTS idx_evaluation_cases_visibility;
ALTER TABLE evaluation_cases
  DROP COLUMN IF EXISTS provenance_json,
  DROP COLUMN IF EXISTS license_metadata,
  DROP COLUMN IF EXISTS source_references,
  DROP COLUMN IF EXISTS choices_json,
  DROP COLUMN IF EXISTS reviewed_by,
  DROP COLUMN IF EXISTS reviewer_status,
  DROP COLUMN IF EXISTS visibility,
  DROP COLUMN IF EXISTS case_type,
  DROP COLUMN IF EXISTS schema_version;
ALTER TABLE evaluation_datasets DROP COLUMN IF EXISTS visibility;
DELETE FROM schema_migrations WHERE version = '0017_evaluation_case_schema';
